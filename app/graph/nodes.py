from langgraph.types import Send
from tenacity import retry, stop_after_attempt, wait_exponential

from app.domain import ckd_guidelines
from app.domain.nutrition import per_serving as _per_serving
from app.domain.schemas import (
    DayResult,
    DaySkeleton,
    FinalizedRecipe,
    IngredientWithNutrients,
    NewRecipeDraft,
    WarningFlag,
    WeekReview,
    WeekSkeleton,
)
from app.graph.llm import get_llm
from app.graph.prompts import (
    build_new_recipe_prompt,
    build_skeleton_prompt,
    build_week_review_prompt,
)
from app.graph.state import GenerationState, RefineDayInput

_MEAL_SLOTS = ("breakfast", "lunch", "dinner")
_NUTRIENT_FIELDS = (
    "calories_kcal",
    "protein_g",
    "salt_g",
    "fat_g",
    "carbs_g",
    "potassium_mg",
    "phosphorus_mg",
)

_retry = retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))


@_retry
def _invoke_structured(llm, schema, prompt: str):
    return llm.with_structured_output(schema).invoke(prompt)


def _finalize_recipe_from_draft(draft: NewRecipeDraft) -> FinalizedRecipe:
    """Sum each ingredient's own nutrient fields into the dish-level totals, instead of
    trusting a single holistic dish-level estimate from the LLM (see NewRecipeDraft)."""
    totals = {field: sum(getattr(ing, field) for ing in draft.ingredients) for field in _NUTRIENT_FIELDS}
    return FinalizedRecipe(
        name=draft.name,
        meal_slot=draft.meal_slot,
        servings=draft.servings,
        ingredients=draft.ingredients,
        instructions=draft.instructions,
        dish_type=draft.dish_type,
        protein_type=draft.protein_type,
        **totals,
    )


def build_skeleton(state: GenerationState) -> dict:
    llm = get_llm("stage1")
    prompt = build_skeleton_prompt(
        profile=state["profile"],
        preferences=state["preferences"],
        calorie_target=state["calorie_target"],
    )
    skeleton: WeekSkeleton = _invoke_structured(llm, WeekSkeleton, prompt)
    return {"week_skeleton": skeleton}


def dispatch_days(state: GenerationState) -> list[Send]:
    return [
        Send(
            "refine_day",
            RefineDayInput(
                day=day,
                profile=state["profile"],
                calorie_target=state["calorie_target"],
            ),
        )
        for day in state["week_skeleton"].days
    ]


# Pure fat (oil) has ~9 kcal/g and contributes essentially no protein or salt, so it's the
# safest way to close a calorie gap on a protein-restricted diet without undoing stage 2's
# protein budget. Capped per serving so "add oil" can't turn into an unrealistic amount.
_KCAL_PER_GRAM_FAT = 9.0
_MAX_ADDED_FAT_G_PER_SERVING = 50.0


def _top_up_with_fat(recipe: FinalizedRecipe, added_kcal_whole_dish: float) -> FinalizedRecipe:
    max_added_fat_whole_dish = _MAX_ADDED_FAT_G_PER_SERVING * recipe.servings
    added_fat_g = min(added_kcal_whole_dish / _KCAL_PER_GRAM_FAT, max_added_fat_whole_dish)
    actual_kcal = added_fat_g * _KCAL_PER_GRAM_FAT
    topped_ingredients = [
        *recipe.ingredients,
        IngredientWithNutrients(
            name="Растительное масло (добавлено для калорийности)",
            amount_g=round(added_fat_g, 1),
            unit="г",
            note="источник дополнительных калорий без белка и соли",
            calories_kcal=actual_kcal,
            protein_g=0.0,
            salt_g=0.0,
            fat_g=added_fat_g,
            carbs_g=0.0,
            potassium_mg=0.0,
            phosphorus_mg=0.0,
        ),
    ]
    return recipe.model_copy(
        update={
            "ingredients": topped_ingredients,
            "calories_kcal": recipe.calories_kcal + actual_kcal,
            "fat_g": recipe.fat_g + added_fat_g,
        }
    )


def refine_day(payload: RefineDayInput) -> dict:
    """Finalize one day: invent all three recipes fresh via Gemini, then scale portions
    up (never down) so the day's calories meet the target floor."""
    day: DaySkeleton = payload["day"]
    profile = payload["profile"]
    calorie_target = payload["calorie_target"]

    # Every meal slot is always generated fresh by the LLM — no reuse-from-library
    # shortcut (the patient explicitly wants every recipe generated from scratch).
    llm = get_llm("stage2")
    recipes: dict[str, FinalizedRecipe] = {}
    for slot_name in _MEAL_SLOTS:
        prompt = build_new_recipe_prompt(day, slot_name, profile, calorie_target)
        draft: NewRecipeDraft = _invoke_structured(llm, NewRecipeDraft, prompt)
        recipes[slot_name] = _finalize_recipe_from_draft(draft)

    # total_* below are PER-SERVING (what the patient actually eats), derived from each
    # recipe's whole-dish figures — see _per_serving.
    total = sum(_per_serving(r.calories_kcal, r.servings) for r in recipes.values())
    adjustment_notes = ""
    if total < calorie_target.min_kcal and total > 0:
        deficit = calorie_target.target_kcal - total
        per_slot_kcal = deficit / len(recipes)
        topped_recipes = {
            # per_slot_kcal is a per-serving shortfall; _top_up_with_fat operates on the
            # whole dish, so scale it up by that recipe's serving count first.
            slot_name: _top_up_with_fat(recipe, per_slot_kcal * recipe.servings)
            for slot_name, recipe in recipes.items()
        }
        new_total = sum(_per_serving(r.calories_kcal, r.servings) for r in topped_recipes.values())
        if new_total > total:
            recipes = topped_recipes
            adjustment_notes = (
                f"Добавлено растительное масло (~{new_total - total:.0f} ккал/порция) для "
                f"достижения нормы калорийности без увеличения белка и соли "
                f"({total:.0f} -> {new_total:.0f} ккал/порция)."
            )
        total = new_total

    day_result = DayResult(
        day_index=day.day_index,
        breakfast=recipes["breakfast"],
        lunch=recipes["lunch"],
        dinner=recipes["dinner"],
        total_calories_kcal=total,
        total_protein_g=sum(_per_serving(r.protein_g, r.servings) for r in recipes.values()),
        total_salt_g=sum(_per_serving(r.salt_g, r.servings) for r in recipes.values()),
        total_fat_g=sum(_per_serving(r.fat_g, r.servings) for r in recipes.values()),
        total_carbs_g=sum(_per_serving(r.carbs_g, r.servings) for r in recipes.values()),
        total_potassium_mg=sum(_per_serving(r.potassium_mg, r.servings) for r in recipes.values()),
        total_phosphorus_mg=sum(_per_serving(r.phosphorus_mg, r.servings) for r in recipes.values()),
        adjustment_notes=adjustment_notes,
    )
    return {"day_results": [day_result]}


def review_week(state: GenerationState) -> dict:
    day_results = sorted(state["day_results"], key=lambda d: d.day_index)
    profile = state["profile"]

    day_summaries = []
    for day in day_results:
        note = f" | заметка: {day.adjustment_notes}" if day.adjustment_notes else ""
        day_summaries.append(
            f"- День {day.day_index}: {day.total_calories_kcal:.0f} ккал, "
            f"белок {day.total_protein_g:.1f} г, соль {day.total_salt_g:.2f} г, "
            f"калий {day.total_potassium_mg:.0f} мг, фосфор {day.total_phosphorus_mg:.0f} мг{note}"
        )

    llm = get_llm("stage3")
    prompt = build_week_review_prompt(profile, day_summaries)
    review: WeekReview = _invoke_structured(llm, WeekReview, prompt)

    # Deterministic safety-net check, merged with the LLM's own flags.
    deterministic_flags: list[WarningFlag] = []
    for day in day_results:
        if day.total_salt_g > profile.salt_limit_g:
            deterministic_flags.append(
                WarningFlag(
                    day_index=day.day_index,
                    metric="salt",
                    severity="warning",
                    message_ru=(
                        f"День {day.day_index}: соль {day.total_salt_g:.2f} г превышает лимит "
                        f"{profile.salt_limit_g} г."
                    ),
                )
            )
        if day.total_protein_g > profile.protein_limit_g * 1.1:
            deterministic_flags.append(
                WarningFlag(
                    day_index=day.day_index,
                    metric="protein",
                    severity="warning",
                    message_ru=(
                        f"День {day.day_index}: белок {day.total_protein_g:.1f} г заметно превышает лимит "
                        f"{profile.protein_limit_g} г."
                    ),
                )
            )
        # Potassium/phosphorus limits are general stage-4 CKD guidance (no doctor-specific
        # numbers exist for these yet), so flag as "info" rather than "warning".
        if day.total_potassium_mg > ckd_guidelines.POTASSIUM_LIMIT_MG_PER_DAY:
            deterministic_flags.append(
                WarningFlag(
                    day_index=day.day_index,
                    metric="potassium",
                    severity="info",
                    message_ru=(
                        f"День {day.day_index}: калий {day.total_potassium_mg:.0f} мг превышает общий "
                        f"ориентир для ХБП 4 стадии ({ckd_guidelines.POTASSIUM_LIMIT_MG_PER_DAY:.0f} мг)."
                    ),
                )
            )
        if day.total_phosphorus_mg > ckd_guidelines.PHOSPHORUS_LIMIT_MG_PER_DAY:
            deterministic_flags.append(
                WarningFlag(
                    day_index=day.day_index,
                    metric="phosphorus",
                    severity="info",
                    message_ru=(
                        f"День {day.day_index}: фосфор {day.total_phosphorus_mg:.0f} мг превышает общий "
                        f"ориентир для ХБП 4 стадии ({ckd_guidelines.PHOSPHORUS_LIMIT_MG_PER_DAY:.0f} мг)."
                    ),
                )
            )

    if deterministic_flags:
        existing = {(f.day_index, f.metric) for f in review.flags}
        for flag in deterministic_flags:
            if (flag.day_index, flag.metric) not in existing:
                review.flags.append(flag)
        review.is_within_limits = False

    # NOTE: day_results uses an operator.add reducer for the Send fan-in, so we must NOT
    # return it here (that would concatenate this sorted copy onto the existing list).
    # Callers should sort state["day_results"] by day_index themselves when consuming it.
    return {"review": review}

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.recipe_dedup import find_duplicate, normalize_name
from app.domain.schemas import DayResult, FinalizedRecipe
from app.models.recipe import Recipe


async def _mark_used(session: AsyncSession, recipe: Recipe) -> None:
    recipe.usage_count += 1
    recipe.last_used_at = datetime.now(UTC)
    session.add(recipe)


async def persist_finalized_recipe(session: AsyncSession, recipe: FinalizedRecipe) -> Recipe:
    """Insert a newly-generated recipe, or reuse an existing row if it's a near-duplicate
    of one already in the library (DB hygiene, not a generation-time shortcut — every
    recipe is always generated fresh by the LLM, see app/graph/nodes.py::refine_day).
    Returns the persisted Recipe row (existing or newly created)."""
    ingredient_names = [ing.name for ing in recipe.ingredients]
    duplicate = await find_duplicate(session, recipe.name, ingredient_names)
    if duplicate is not None:
        existing = await session.get(Recipe, duplicate.id)
        if existing is not None:
            await _mark_used(session, existing)
            return existing

    new_recipe = Recipe(
        name=recipe.name,
        normalized_name=normalize_name(recipe.name),
        instructions=recipe.instructions,
        meal_slots=[recipe.meal_slot],
        dish_type=recipe.dish_type,
        protein_type=recipe.protein_type,
        tags=[],
        servings=recipe.servings,
        ingredients=[ing.model_dump() for ing in recipe.ingredients],
        calories_kcal=recipe.calories_kcal,
        protein_g=recipe.protein_g,
        salt_g=recipe.salt_g,
        fat_g=recipe.fat_g,
        carbs_g=recipe.carbs_g,
        potassium_mg=recipe.potassium_mg,
        phosphorus_mg=recipe.phosphorus_mg,
        usage_count=1,
        last_used_at=datetime.now(UTC),
        source="generated",
    )
    session.add(new_recipe)
    await session.flush()
    return new_recipe


async def persist_day_result(session: AsyncSession, day_result: DayResult) -> dict[str, Recipe]:
    """Persist/reuse the three recipes of a day. Returns {meal_slot: Recipe}."""
    return {
        "breakfast": await persist_finalized_recipe(session, day_result.breakfast),
        "lunch": await persist_finalized_recipe(session, day_result.lunch),
        "dinner": await persist_finalized_recipe(session, day_result.dinner),
    }


async def list_recipes(
    session: AsyncSession,
    meal_slot: str | None = None,
    dish_type: str | None = None,
    protein_type: str | None = None,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Recipe]:
    stmt = select(Recipe).order_by(Recipe.name)
    if meal_slot:
        stmt = stmt.where(Recipe.meal_slots.any(meal_slot))
    if dish_type:
        stmt = stmt.where(Recipe.dish_type == dish_type)
    if protein_type:
        stmt = stmt.where(Recipe.protein_type == protein_type)
    if query:
        stmt = stmt.where(Recipe.name.ilike(f"%{query}%"))
    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_recipe(session: AsyncSession, recipe_id: int) -> Recipe | None:
    return await session.get(Recipe, recipe_id)

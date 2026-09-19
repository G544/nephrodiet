from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.nutrition import calculate_calorie_target, per_serving
from app.domain.schemas import CalorieTargetInput, ProfileInput
from app.graph.graph import generate_week
from app.models.menu import MenuDay, MenuWarning, WeeklyMenu
from app.services import profile_service, recipe_service
from app.services.preference_service import list_preferences


class NoProfileError(Exception):
    pass


def _to_profile_input(profile) -> ProfileInput:
    return ProfileInput(
        age=profile.age,
        weight_kg=profile.weight_kg,
        height_cm=profile.height_cm,
        sex=profile.sex,
        activity_level=profile.activity_level,
        egfr=profile.egfr or 0.0,
        salt_limit_g=profile.salt_limit_g,
        protein_limit_g=profile.protein_limit_g,
        goal=profile.goal,
    )


async def generate_weekly_menu(session: AsyncSession, week_start_date: date | None = None) -> WeeklyMenu:
    profile = await profile_service.get_profile(session)
    if profile is None:
        raise NoProfileError("Profile is not set up yet")

    preferences = await list_preferences(session, active_only=True)
    preference_phrases = [p.phrase for p in preferences]

    profile_input = _to_profile_input(profile)
    target = calculate_calorie_target(
        weight_kg=profile_input.weight_kg,
        height_cm=profile_input.height_cm,
        age=profile_input.age,
        sex=profile_input.sex,
        activity_level=profile_input.activity_level,
        goal=profile_input.goal,
    )
    calorie_target = CalorieTargetInput(
        target_kcal=target.target_kcal, min_kcal=target.min_kcal, max_kcal=target.max_kcal
    )

    result = await generate_week(
        profile=profile_input,
        preferences=preference_phrases,
        calorie_target=calorie_target,
    )

    weekly_menu = WeeklyMenu(
        week_start_date=week_start_date or datetime.now(UTC).date(),
        status="final",
        calorie_target_kcal=calorie_target.target_kcal,
        calorie_target_min=calorie_target.min_kcal,
        calorie_target_max=calorie_target.max_kcal,
        profile_snapshot=profile_input.model_dump() | {"preferences": preference_phrases},
        review_status="ok" if result.review.is_within_limits else "warning",
        review_summary_ru=result.review.summary_ru,
    )
    session.add(weekly_menu)
    await session.flush()

    for day_result in result.day_results:
        persisted = await recipe_service.persist_day_result(session, day_result)
        finalized = {
            "breakfast": day_result.breakfast,
            "lunch": day_result.lunch,
            "dinner": day_result.dinner,
        }
        meals_snapshot = {
            slot: {
                "recipe_id": persisted[slot].id,
                "name": finalized[slot].name,
                "servings": finalized[slot].servings,
                # Ingredients/instructions stay for the whole recipe (all servings) — only
                # the nutrition figures below are per-serving (what the patient eats).
                "ingredients": [ing.model_dump() for ing in finalized[slot].ingredients],
                "instructions": finalized[slot].instructions,
                "calories_kcal": per_serving(finalized[slot].calories_kcal, finalized[slot].servings),
                "protein_g": per_serving(finalized[slot].protein_g, finalized[slot].servings),
                "salt_g": per_serving(finalized[slot].salt_g, finalized[slot].servings),
                "fat_g": per_serving(finalized[slot].fat_g, finalized[slot].servings),
                "carbs_g": per_serving(finalized[slot].carbs_g, finalized[slot].servings),
                "potassium_mg": per_serving(finalized[slot].potassium_mg, finalized[slot].servings),
                "phosphorus_mg": per_serving(finalized[slot].phosphorus_mg, finalized[slot].servings),
            }
            for slot in ("breakfast", "lunch", "dinner")
        }
        menu_day = MenuDay(
            weekly_menu_id=weekly_menu.id,
            day_index=day_result.day_index,
            date=weekly_menu.week_start_date + timedelta(days=day_result.day_index),
            breakfast_recipe_id=persisted["breakfast"].id,
            lunch_recipe_id=persisted["lunch"].id,
            dinner_recipe_id=persisted["dinner"].id,
            meals=meals_snapshot,
            total_calories_kcal=day_result.total_calories_kcal,
            total_protein_g=day_result.total_protein_g,
            total_salt_g=day_result.total_salt_g,
            total_fat_g=day_result.total_fat_g,
            total_carbs_g=day_result.total_carbs_g,
            total_potassium_mg=day_result.total_potassium_mg,
            total_phosphorus_mg=day_result.total_phosphorus_mg,
            adjustment_notes=day_result.adjustment_notes,
        )
        session.add(menu_day)

    for flag in result.review.flags:
        session.add(
            MenuWarning(
                weekly_menu_id=weekly_menu.id,
                day_index=None if flag.day_index < 0 else flag.day_index,
                metric=flag.metric,
                severity=flag.severity,
                message_ru=flag.message_ru,
            )
        )

    await session.commit()
    await session.refresh(weekly_menu)
    return weekly_menu


async def list_weekly_menus(session: AsyncSession) -> list[WeeklyMenu]:
    result = await session.execute(select(WeeklyMenu).order_by(WeeklyMenu.created_at.desc()))
    return list(result.scalars())


async def get_weekly_menu(session: AsyncSession, menu_id: int) -> WeeklyMenu | None:
    return await session.get(WeeklyMenu, menu_id)


async def get_menu_days(session: AsyncSession, menu_id: int) -> list[MenuDay]:
    result = await session.execute(
        select(MenuDay).where(MenuDay.weekly_menu_id == menu_id).order_by(MenuDay.day_index)
    )
    return list(result.scalars())


async def get_menu_warnings(session: AsyncSession, menu_id: int) -> list[MenuWarning]:
    result = await session.execute(
        select(MenuWarning).where(MenuWarning.weekly_menu_id == menu_id)
    )
    return list(result.scalars())

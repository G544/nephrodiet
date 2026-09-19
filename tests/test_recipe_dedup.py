import pytest
from sqlalchemy import text

from app.db.session import async_session_factory
from app.domain.recipe_dedup import (
    find_duplicate,
    ingredient_jaccard,
    is_duplicate,
    normalize_name,
)


def test_normalize_name_strips_punctuation_and_case():
    assert normalize_name("  Куриный Суп, с овощами!! ") == "куриный суп с овощами"


def test_normalize_name_collapses_whitespace():
    assert normalize_name("Гречка   с   грибами") == "гречка с грибами"


def test_ingredient_jaccard_identical_sets():
    assert ingredient_jaccard(["курица", "морковь"], ["Курица", "Морковь"]) == pytest.approx(1.0)


def test_ingredient_jaccard_disjoint_sets():
    assert ingredient_jaccard(["курица"], ["говядина"]) == pytest.approx(0.0)


def test_ingredient_jaccard_empty_is_zero():
    assert ingredient_jaccard([], ["курица"]) == 0.0


def test_is_duplicate_high_name_similarity_alone():
    assert is_duplicate(name_similarity=0.7, jaccard=0.0) is True


def test_is_duplicate_weak_name_needs_ingredient_overlap():
    assert is_duplicate(name_similarity=0.45, jaccard=0.6) is True
    assert is_duplicate(name_similarity=0.45, jaccard=0.2) is False


def test_is_duplicate_low_similarity_never_duplicate():
    assert is_duplicate(name_similarity=0.2, jaccard=0.9) is False


@pytest.mark.asyncio
async def test_find_duplicate_against_real_postgres():
    async with async_session_factory() as session:
        await session.execute(text("DELETE FROM recipe WHERE name LIKE 'ТЕСТ %'"))
        await session.execute(
            text(
                """
                INSERT INTO recipe (
                    name, normalized_name, description, instructions, meal_slots,
                    dish_type, protein_type, tags, servings, ingredients,
                    calories_kcal, protein_g, salt_g, fat_g, carbs_g,
                    usage_count, source, created_at, updated_at
                ) VALUES (
                    'ТЕСТ Куриный суп с овощами', 'тест куриный суп с овощами', '', 'варить',
                    '{lunch}', 'soup', 'chicken', '{}', 2,
                    '[{"name": "курица"}, {"name": "морковь"}, {"name": "картофель"}]'::jsonb,
                    400, 30, 2, 10, 20, 0, 'generated', now(), now()
                )
                """
            )
        )
        await session.commit()

        duplicate = await find_duplicate(
            session,
            "ТЕСТ Куриный суп с овощами и зеленью",
            ["курица", "морковь", "картофель", "укроп"],
        )
        assert duplicate is not None
        assert duplicate.name == "ТЕСТ Куриный суп с овощами"

        no_match = await find_duplicate(session, "ТЕСТ Овсянка с ягодами", ["овсянка", "ягоды"])
        assert no_match is None

        await session.execute(text("DELETE FROM recipe WHERE name LIKE 'ТЕСТ %'"))
        await session.commit()

import streamlit as st

from app.services import recipe_service
from app.ui.runtime import run_db

MEAL_SLOTS = {"": "Любой приём пищи", "breakfast": "Завтрак", "lunch": "Обед", "dinner": "Ужин"}


def render() -> None:
    st.title("Библиотека рецептов")

    col1, col2, col3, col4 = st.columns(4)
    q = col1.text_input("Поиск по названию")
    meal_slot = col2.selectbox("Приём пищи", list(MEAL_SLOTS), format_func=MEAL_SLOTS.get)
    dish_type = col3.text_input("Тип блюда")
    protein_type = col4.text_input("Тип белка")

    recipes = run_db(
        recipe_service.list_recipes,
        meal_slot=meal_slot or None,
        dish_type=dish_type.strip() or None,
        protein_type=protein_type.strip() or None,
        query=q.strip() or None,
        limit=200,
    )
    if not recipes:
        st.write("Рецепты не найдены.")
        return

    for recipe in recipes:
        servings = recipe.servings or 1
        with st.expander(f"{recipe.name} — {recipe.dish_type} · {recipe.protein_type}"):
            st.caption(f"Приёмы пищи: {', '.join(recipe.meal_slots)}")
            st.write(
                f"Пищевая ценность **на 1 порцию** (рецепт на {recipe.servings} порции): "
                f"{recipe.calories_kcal / servings:.0f} ккал, "
                f"белок {recipe.protein_g / servings:.1f} г, "
                f"соль {recipe.salt_g / servings:.2f} г, "
                f"жиры {recipe.fat_g / servings:.1f} г, "
                f"углеводы {recipe.carbs_g / servings:.1f} г, "
                f"калий {recipe.potassium_mg / servings:.0f} мг, "
                f"фосфор {recipe.phosphorus_mg / servings:.0f} мг"
            )
            st.markdown(f"**Ингредиенты (на {recipe.servings} порции)**")
            st.markdown(
                "\n".join(
                    f"- {i['name']} — {i['amount_g']:.0f} {i['unit']}"
                    + (f" ({i['note']})" if i.get("note") else "")
                    for i in recipe.ingredients
                )
            )
            st.markdown("**Приготовление**")
            st.write(recipe.instructions)
            last_used = f", последний раз {recipe.last_used_at:%Y-%m-%d}" if recipe.last_used_at else ""
            st.caption(f"Использован {recipe.usage_count} раз(а){last_used}")

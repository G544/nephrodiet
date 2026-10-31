import streamlit as st

from app.services import menu_service
from app.ui.menu_format import (
    SLOTS,
    day_name,
    day_title_stats,
    ingredient_line,
    meal_nutrition_line,
)
from app.ui.menu_pdf import build_menu_pdf
from app.ui.runtime import run_db


def _render_meal(label: str, meal: dict) -> None:
    st.markdown(f"**{label}: {meal['name']}**")
    st.caption(meal_nutrition_line(meal))
    with st.expander(f"Ингредиенты (на {meal.get('servings', 2)} порции) и приготовление"):
        st.markdown("\n".join(f"- {ingredient_line(ing)}" for ing in meal["ingredients"]))
        st.write(meal["instructions"])


def render() -> None:
    st.title("Меню")
    menus = run_db(menu_service.list_weekly_menus)
    if not menus:
        st.info("Меню ещё не создавались.")
        return

    ids = [m.id for m in menus]
    by_id = {m.id: m for m in menus}
    preselect = st.session_state.pop("selected_menu_id", None)
    if preselect in ids:
        st.session_state["menu_select"] = preselect

    def label(menu_id: int) -> str:
        m = by_id[menu_id]
        flag = " ⚠" if m.review_status == "warning" else ""
        return f"Неделя с {m.week_start_date}{flag}"

    menu_id = st.selectbox("Меню", ids, format_func=label, key="menu_select")
    menu = by_id[menu_id]
    days = run_db(menu_service.get_menu_days, menu_id)
    warnings = run_db(menu_service.get_menu_warnings, menu_id)

    st.subheader(f"Меню с {menu.week_start_date}")
    st.write(
        f"Целевая калорийность: {menu.calorie_target_kcal:.0f} ккал/день "
        f"(минимум {menu.calorie_target_min:.0f}, максимум {menu.calorie_target_max:.0f})"
    )

    if menu.review_status == "warning":
        lines = [f"**⚠ Проверка недели выявила проблемы:** {menu.review_summary_ru}"]
        for w in warnings:
            prefix = f"{day_name(w.day_index)}: " if w.day_index is not None else ""
            lines.append(f"- {prefix}{w.message_ru}")
        st.warning("\n".join(lines))
    else:
        st.success(menu.review_summary_ru or "Неделя в пределах ограничений.")

    st.download_button(
        "Скачать меню на неделю (PDF)",
        data=build_menu_pdf(menu, days, warnings),
        file_name=f"menu_{menu.week_start_date}.pdf",
        mime="application/pdf",
    )

    for day in days:
        title = f"{day_name(day.day_index)} ({day.date}) — {day_title_stats(day)}"
        with st.expander(title, expanded=day.day_index == 0):
            if day.adjustment_notes:
                st.caption(day.adjustment_notes)
            for slot, slot_label in SLOTS:
                _render_meal(slot_label, day.meals[slot])
                st.divider()

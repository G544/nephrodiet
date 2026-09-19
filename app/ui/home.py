import streamlit as st

from app.config import get_settings
from app.services import menu_service, profile_service
from app.ui.runtime import run_db


def render() -> None:
    from app.ui import nav

    st.title("Нефродиета")

    profile = run_db(profile_service.get_profile)
    if profile is None:
        st.info("Профиль ещё не заполнен.")
        if st.button("Заполнить профиль", type="primary"):
            st.switch_page(nav.profile_page)
        return

    goal = "набор веса" if profile.goal == "weight_gain" else "удержание веса"
    st.write(
        f"Цель: {goal} · лимит соли {profile.salt_limit_g} г/день · "
        f"лимит белка {profile.protein_limit_g} г/день"
    )
    st.caption(
        "Также учитываются общие ограничения по калию и фосфору для ХБП 4 стадии "
        "(точных цифр от врача по ним пока нет — используются стандартные ориентиры)."
    )

    if not get_settings().gemini_api_key:
        st.warning("GEMINI_API_KEY не задан — генерация меню недоступна.")
    elif st.button("Сгенерировать меню на неделю", type="primary"):
        try:
            with st.spinner("Генерация меню, это может занять несколько минут…"):
                menu = run_db(menu_service.generate_weekly_menu)
        except Exception as exc:  # noqa: BLE001 — surface any LLM/DB failure in the UI
            st.error(f"Не удалось сгенерировать меню: {exc}")
        else:
            st.session_state["selected_menu_id"] = menu.id
            st.switch_page(nav.menus_page)

    menus = run_db(menu_service.list_weekly_menus)
    if menus:
        latest = menus[0]
        st.subheader("Последнее меню")
        status = "⚠ есть предупреждения" if latest.review_status == "warning" else "норма"
        st.write(f"Неделя с {latest.week_start_date} · {status}")
        if st.button("Открыть", type="secondary"):
            st.session_state["selected_menu_id"] = latest.id
            st.switch_page(nav.menus_page)

import hmac

import streamlit as st

from app.config import get_settings
from app.ui import home, menus, profile, recipes

home_page = st.Page(home.render, title="Главная", icon="🏠", url_path="home", default=True)
profile_page = st.Page(profile.render, title="Профиль", icon="👤", url_path="profile")
menus_page = st.Page(menus.render, title="Меню", icon="🍽️", url_path="menus")
recipes_page = st.Page(recipes.render, title="Рецепты", icon="📖", url_path="recipes")


def _password_ok() -> bool:
    """Optional gate: set APP_PASSWORD in secrets to protect the (single-user) medical profile."""
    expected = get_settings().app_password
    if not expected or st.session_state.get("authenticated"):
        return True
    entered = st.text_input("Пароль", type="password")
    if entered:
        if hmac.compare_digest(entered.encode(), expected.encode()):
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("Неверный пароль.")
    return False


def run() -> None:
    if not _password_ok():
        st.stop()
    st.navigation([home_page, profile_page, menus_page, recipes_page]).run()

import streamlit as st

from app.services import preference_service, profile_service
from app.ui.runtime import run_db

ACTIVITY_CHOICES = {
    "sedentary": "Малоподвижный",
    "light": "Лёгкая активность",
    "moderate": "Умеренная активность",
    "active": "Высокая активность",
}
SEX_CHOICES = {"male": "Мужской", "female": "Женский"}
GOAL_CHOICES = {"maintenance": "Удержание веса", "weight_gain": "Набор веса"}


def _select(label: str, choices: dict[str, str], current: str | None):
    keys = list(choices)
    index = keys.index(current) if current in keys else 0
    return st.selectbox(label, keys, index=index, format_func=choices.get)


def render() -> None:
    st.title("Профиль")
    profile = run_db(profile_service.get_profile)

    with st.form("profile"):
        col1, col2, col3 = st.columns(3)
        age = col1.number_input("Возраст", 1, 120, profile.age if profile else 58)
        weight = col2.number_input("Вес, кг", 20.0, 300.0, profile.weight_kg if profile else 72.0, 0.1)
        height = col3.number_input("Рост, см", 100.0, 250.0, profile.height_cm if profile else 172.0, 0.1)

        col1, col2, col3 = st.columns(3)
        with col1:
            sex = _select("Пол", SEX_CHOICES, profile.sex if profile else None)
        with col2:
            activity = _select("Активность", ACTIVITY_CHOICES, profile.activity_level if profile else None)
        with col3:
            goal = _select("Цель", GOAL_CHOICES, profile.goal if profile else None)

        col1, col2, col3 = st.columns(3)
        egfr = col1.number_input(
            "СКФ (контекст для ИИ)",
            0.0,
            200.0,
            (profile.egfr or 0.0) if profile else 0.0,
            0.1,
            help="0 — не указывать",
        )
        salt = col2.number_input("Лимит соли, г/день", 0.0, 30.0, profile.salt_limit_g if profile else 5.0, 0.1)
        protein = col3.number_input(
            "Лимит белка, г/день", 0.0, 300.0, profile.protein_limit_g if profile else 60.0, 0.1
        )

        if st.form_submit_button("Сохранить профиль", type="primary"):
            run_db(
                profile_service.upsert_profile,
                {
                    "age": int(age),
                    "weight_kg": weight,
                    "height_cm": height,
                    "sex": sex,
                    "activity_level": activity,
                    "egfr": egfr or None,
                    "salt_limit_g": salt,
                    "protein_limit_g": protein,
                    "goal": goal,
                },
            )
            st.success("Профиль сохранён.")

    st.divider()
    st.subheader("Пожелания")

    with st.form("add_preference", clear_on_submit=True):
        phrase = st.text_input("Новое пожелание", placeholder="например: суп раз в неделю")
        if st.form_submit_button("Добавить") and phrase.strip():
            run_db(preference_service.add_preference, phrase.strip())
            st.rerun()

    preferences = run_db(preference_service.list_preferences)
    if not preferences:
        st.write("Пожеланий пока нет.")
    for preference in preferences:
        text_col, button_col = st.columns([8, 1], vertical_alignment="center")
        text_col.write(preference.phrase)
        if button_col.button("✕", key=f"del_pref_{preference.id}", help="Удалить пожелание"):
            run_db(preference_service.delete_preference, preference.id)
            st.rerun()

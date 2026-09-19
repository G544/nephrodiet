import streamlit as st

# Must be imported before anything reads app.config: it copies Streamlit secrets into env vars.
from app.ui import runtime  # noqa: F401
from app.ui.nav import run

st.set_page_config(page_title="Нефродиета", page_icon="🥗", layout="centered")
run()

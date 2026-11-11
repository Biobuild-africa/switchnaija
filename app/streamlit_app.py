"""SwitchNaija web app (BioBuild Africa). Run:  streamlit run app/streamlit_app.py"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))  # so views can `import ui`
import ui  # noqa: E402

st.set_page_config(page_title="SwitchNaija | BioBuild Africa", page_icon="🌱", layout="wide",
                   initial_sidebar_state="collapsed")
ui.setup()

views = Path(__file__).parent / "views"
pages = [
    st.Page(views / "home.py", title="Home", url_path="", default=True),
    st.Page(views / "energy.py", title="Energy Planner", url_path="energy"),
    st.Page(views / "battery.py", title="Battery Afterlife", url_path="battery"),
    st.Page(views / "flood.py", title="FloodSafe", url_path="flood"),
]
st.navigation(pages, position="hidden").run()

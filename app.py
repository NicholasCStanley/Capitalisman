"""AutoCapital: Price Prediction & Backtesting App."""

import streamlit as st

st.set_page_config(
    page_title="AutoCapital",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Importing indicators triggers auto-registration via indicators/__init__.py
import indicators  # noqa: F401, E402

from ui import page_predict, page_backtest, page_explore  # noqa: E402

# Sidebar navigation
st.sidebar.title("AutoCapital")
page = st.sidebar.radio(
    "Navigation",
    ["Predict", "Backtest", "Explore"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")

if page == "Predict":
    page_predict.render()
elif page == "Backtest":
    page_backtest.render()
elif page == "Explore":
    page_explore.render()

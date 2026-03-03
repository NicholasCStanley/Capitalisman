"""Shared UI widgets for sidebar controls."""

import streamlit as st

from config.settings import (
    DEFAULT_BACKTEST_PERIOD,
    DEFAULT_COST_PER_TRADE_PCT,
    DEFAULT_INITIAL_CAPITAL,
    DEFAULT_PERIOD,
    DEFAULT_PREDICTION_HORIZON,
    INTRADAY_WARNINGS,
    INTERVALS,
    PERIODS,
)
from indicators.registry import get_all_indicators


def ticker_input(key: str = "ticker") -> str:
    """Render ticker input and return the value."""
    return st.text_input(
        "Ticker Symbol",
        value="AAPL",
        key=key,
        help="Enter a stock (AAPL) or crypto (BTC-USD) ticker",
    ).upper().strip()


def period_select(key: str = "period", default: str = DEFAULT_PERIOD) -> str:
    """Render period selector."""
    idx = PERIODS.index(default) if default in PERIODS else 3
    return st.selectbox("Period", PERIODS, index=idx, key=key)


def interval_select(key: str = "interval") -> str:
    """Render interval selector."""
    return st.selectbox("Interval", INTERVALS, index=4, key=key)  # default "1d"


def horizon_input(key: str = "horizon") -> int:
    """Render prediction horizon slider."""
    return st.slider(
        "Prediction Horizon (days)",
        min_value=1,
        max_value=30,
        value=DEFAULT_PREDICTION_HORIZON,
        key=key,
    )


def indicator_picker(key: str = "indicators") -> list[str]:
    """Render indicator multi-select and return chosen names."""
    all_indicators = get_all_indicators()
    names = sorted(all_indicators.keys())
    return st.multiselect(
        "Indicators",
        options=names,
        default=names,
        key=key,
    )


def check_data_sufficiency(
    df_len: int,
    selected_indicators: list[str],
) -> list[str]:
    """Check which selected indicators lack sufficient data.

    Returns a list of warning strings for indicators that need more bars
    than the dataframe provides. Returns empty list if all are fine.
    """
    all_indicators = get_all_indicators()
    warnings = []
    for name in selected_indicators:
        if name not in all_indicators:
            continue
        indicator = all_indicators[name]
        if df_len < indicator.lookback:
            warnings.append(
                f"**{name}** needs {indicator.lookback} bars, got {df_len}"
            )
    return warnings


def capital_input(key: str = "capital") -> float:
    """Render initial capital input."""
    return st.number_input(
        "Initial Capital ($)",
        min_value=100.0,
        max_value=10_000_000.0,
        value=DEFAULT_INITIAL_CAPITAL,
        step=1000.0,
        key=key,
    )


def cost_input(key: str = "cost") -> float:
    """Render transaction cost input (round-trip %)."""
    return st.number_input(
        "Transaction Cost (%)",
        min_value=0.0,
        max_value=5.0,
        value=DEFAULT_COST_PER_TRADE_PCT,
        step=0.05,
        key=key,
        help="Round-trip cost per trade (slippage + commission) as a percentage",
    )


def show_interval_warning(interval: str) -> None:
    """Show a warning if the selected interval has data limits."""
    warning = INTRADAY_WARNINGS.get(interval)
    if warning:
        st.caption(f"⚠ {warning}")


_MAX_RECENT = 8


def record_recent_ticker(ticker: str) -> None:
    """Add a ticker to the recent tickers list in session state."""
    if not ticker:
        return
    if "recent_tickers" not in st.session_state:
        st.session_state["recent_tickers"] = []
    recents = st.session_state["recent_tickers"]
    # Move to front if already present, otherwise prepend
    if ticker in recents:
        recents.remove(ticker)
    recents.insert(0, ticker)
    st.session_state["recent_tickers"] = recents[:_MAX_RECENT]


def render_recent_tickers(input_key: str) -> None:
    """Render quick-select buttons for recent tickers.

    When clicked, sets the value of the ticker input identified by input_key.
    """
    recents = st.session_state.get("recent_tickers", [])
    # Don't show the ticker that's currently in the input
    current = st.session_state.get(input_key, "")
    visible = [t for t in recents if t != current]
    if not visible:
        return
    st.caption("Recent:")
    cols = st.columns(min(len(visible), 4))
    for i, ticker in enumerate(visible[:4]):
        if cols[i].button(ticker, key=f"recent_{input_key}_{ticker}"):
            st.session_state[input_key] = ticker
            st.rerun()

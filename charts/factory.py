"""Chart factory: try TradingView, fall back to Plotly."""

from typing import Any

import pandas as pd
import streamlit as st

from charts import tradingview
from charts.plotly_fallback import create_candlestick_chart, create_equity_curve


def render_price_chart(
    df: pd.DataFrame,
    title: str = "",
    overlays: list[dict[str, Any]] | None = None,
    subplots: list[dict[str, Any]] | None = None,
    markers: list[dict[str, Any]] | None = None,
    height: int = 800,
    use_tv: bool = True,
) -> None:
    """Render a price chart in Streamlit using TradingView or Plotly fallback.

    If TradingView is available and use_tv=True, uses it (but without subplots
    or markers — those fall back to Plotly automatically).
    """
    # TradingView can handle basic charts with overlays
    # Fall back to Plotly if we need subplots or markers
    if use_tv and tradingview.is_available() and not subplots and not markers:
        chart = tradingview.create_tv_chart(
            df, title=title, overlays=overlays, height=height
        )
        if chart is not None:
            chart.load()
            return

    # Plotly fallback (or full-featured chart)
    fig = create_candlestick_chart(
        df,
        title=title,
        overlays=overlays,
        subplots=subplots,
        markers=markers,
        height=height,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_equity_curve(
    equity: pd.Series,
    title: str = "Equity Curve",
    height: int = 400,
) -> None:
    """Render an equity curve chart in Streamlit."""
    fig = create_equity_curve(equity, title=title, height=height)
    st.plotly_chart(fig, use_container_width=True)

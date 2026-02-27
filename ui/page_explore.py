"""Explore page: interactive data exploration and charting."""

import streamlit as st

from charts.factory import render_price_chart
from data.fetcher import fetch_ohlcv, get_asset_info
from indicators.registry import get_all_indicators
from ui.components import check_data_sufficiency, indicator_picker, interval_select, period_select, ticker_input


def render():
    st.header("Explore")

    # Sidebar controls
    with st.sidebar:
        ticker = ticker_input(key="explore_ticker")
        period = period_select(key="explore_period")
        interval = interval_select(key="explore_interval")
        selected_indicators = indicator_picker(key="explore_indicators")

    if not ticker:
        st.info("Enter a ticker symbol in the sidebar to get started.")
        return

    # Fetch data
    try:
        with st.spinner("Fetching data..."):
            df = fetch_ohlcv(ticker, period=period, interval=interval)
    except ValueError as e:
        st.error(str(e))
        return

    # Asset info card
    info = get_asset_info(ticker)
    if info:
        cols = st.columns(4)
        cols[0].metric("Name", info["name"])
        cols[1].metric("Sector", info["sector"])
        if info.get("52w_high"):
            cols[2].metric("52W High", f"${info['52w_high']:,.2f}")
        if info.get("52w_low"):
            cols[3].metric("52W Low", f"${info['52w_low']:,.2f}")

    # Check data sufficiency
    data_warnings = check_data_sufficiency(len(df), selected_indicators)
    if data_warnings:
        st.warning(
            f"Insufficient data for {len(data_warnings)} indicator(s) "
            f"({len(df)} bars available):\n\n" + "\n".join(f"- {w}" for w in data_warnings)
            + "\n\nUse a longer period or wider interval for full indicator coverage."
        )

    # Compute selected indicators
    all_indicators = get_all_indicators()
    overlays = []
    subplot_configs = []
    computed_df = df.copy()

    for name in selected_indicators:
        if name not in all_indicators:
            continue
        indicator = all_indicators[name]
        computed_df = indicator.compute(computed_df)
        chart_cfg = indicator.get_chart_config()

        if chart_cfg.get("overlay"):
            overlays.append(chart_cfg)
        else:
            subplot_configs.append(chart_cfg)

    # Render chart
    render_price_chart(
        computed_df,
        title=f"{ticker} — {period} ({interval})",
        overlays=overlays,
        subplots=subplot_configs,
        height=700,
    )

    # Raw data table
    with st.expander("Raw Data", expanded=False):
        st.dataframe(
            computed_df.tail(100).style.format("{:.2f}", subset=["Open", "High", "Low", "Close"]),
            use_container_width=True,
        )

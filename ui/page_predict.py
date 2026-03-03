"""Predict page: signal generation and display."""

import streamlit as st

from charts.factory import render_price_chart
from data.fetcher import fetch_with_warmup
from indicators.registry import get_all_indicators
from signals.base import SignalDirection
from signals.combiner import combine_signals
from ui.components import (
    advanced_settings,
    check_data_sufficiency,
    horizon_input,
    indicator_picker,
    period_select,
    record_recent_ticker,
    render_recent_tickers,
    ticker_input,
)


def _signal_color(direction: SignalDirection) -> str:
    if direction == SignalDirection.BUY:
        return "#4CAF50"
    elif direction == SignalDirection.SELL:
        return "#F44336"
    return "#FFC107"


def _signal_emoji(direction: SignalDirection) -> str:
    if direction == SignalDirection.BUY:
        return "▲"
    elif direction == SignalDirection.SELL:
        return "▼"
    return "●"


def render():
    st.header("Predict")

    # Sidebar controls
    with st.sidebar:
        ticker = ticker_input(key="predict_ticker")
        render_recent_tickers("predict_ticker")
        period = period_select(key="predict_period")
        horizon = horizon_input(key="predict_horizon")
        selected_indicators = indicator_picker(key="predict_indicators")
        advanced_settings(key_prefix="predict_adv")

    if not ticker:
        st.info("Enter a ticker symbol in the sidebar to get started.")
        return

    if not selected_indicators:
        st.warning("Select at least one indicator.")
        return

    record_recent_ticker(ticker)

    # Fetch data with warmup for short periods
    try:
        with st.spinner("Fetching data..."):
            full_df, display_df = fetch_with_warmup(ticker, period=period)
    except ValueError as e:
        st.error(str(e))
        return
    except Exception as e:
        st.error(f"Unexpected error fetching data: {e}")
        return

    try:
        # Check data sufficiency against full (warmup) data
        data_warnings = check_data_sufficiency(len(full_df), selected_indicators)
        if data_warnings:
            st.warning(
                f"Insufficient data for {len(data_warnings)} indicator(s) "
                f"({len(full_df)} bars available):\n\n" + "\n".join(f"- {w}" for w in data_warnings)
                + "\n\nThese will report HOLD. Use a longer period for full analysis."
            )

        # Build selected indicators
        all_indicators = get_all_indicators()
        chosen = {n: all_indicators[n] for n in selected_indicators if n in all_indicators}

        # Compute indicators on full data (includes warmup)
        computed_df = full_df.copy()
        for name, indicator in chosen.items():
            computed_df = indicator.compute(computed_df)

        # Generate combined signal from full data
        signal = combine_signals(chosen, computed_df, horizon_days=horizon, precomputed=True)

        # Trim computed data to display range for charting
        computed_display = computed_df.iloc[-len(display_df):]
    except Exception as e:
        st.error(f"Error computing signals: {e}")
        return

    # Multi-timeframe signal cards (1d, 5d, 20d)
    _MTF_HORIZONS = [("1d", 1), ("5d", 5), ("20d", 20)]
    mtf_cols = st.columns(len(_MTF_HORIZONS))
    for col, (label, h) in zip(mtf_cols, _MTF_HORIZONS):
        mtf_signal = combine_signals(chosen, computed_df, horizon_days=h, precomputed=True)
        mtf_color = _signal_color(mtf_signal.direction)
        mtf_arrow = _signal_emoji(mtf_signal.direction)
        with col:
            st.markdown(
                f"""
                <div style="
                    border: 1px solid {mtf_color};
                    border-radius: 8px;
                    padding: 12px;
                    text-align: center;
                    margin-bottom: 12px;
                ">
                    <p style="font-size: 0.85em; color: #999; margin: 0;">{label}</p>
                    <p style="color: {mtf_color}; font-weight: bold; font-size: 1.2em; margin: 4px 0;">
                        {mtf_arrow} {mtf_signal.direction.value}
                    </p>
                    <p style="font-size: 0.85em; color: #ccc; margin: 0;">
                        {mtf_signal.confidence:.0%}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Primary signal card
    color = _signal_color(signal.direction)
    arrow = _signal_emoji(signal.direction)

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {color}22, {color}11);
            border: 2px solid {color};
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            margin-bottom: 20px;
        ">
            <h1 style="color: {color}; margin: 0;">
                {arrow} {signal.direction.value}
            </h1>
            <p style="font-size: 1.3em; color: #ccc; margin: 8px 0 0 0;">
                Confidence: {signal.confidence:.0%}
            </p>
            <p style="font-size: 0.9em; color: #999; margin: 4px 0 0 0;">
                {horizon}-day horizon &bull; {len(selected_indicators)} indicators
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Reasoning narrative
    if signal.reasoning:
        st.markdown(f"**Analysis:** {signal.reasoning}")

    # Score breakdown
    col1, col2, col3 = st.columns(3)
    col1.metric("BUY Score", f"{signal.scores.get('BUY', 0):.2f}")
    col2.metric("SELL Score", f"{signal.scores.get('SELL', 0):.2f}")
    col3.metric("HOLD Score", f"{signal.scores.get('HOLD', 0):.2f}")

    # Chart
    overlays = []
    subplot_configs = []
    for name, indicator in chosen.items():
        chart_cfg = indicator.get_chart_config()
        if chart_cfg.get("overlay"):
            overlays.append(chart_cfg)
        else:
            subplot_configs.append(chart_cfg)

    render_price_chart(
        computed_display,
        title=f"{ticker} — Signal: {signal.direction.value}",
        overlays=overlays,
        subplots=subplot_configs,
        height=700,
    )

    # Indicator breakdown table
    st.subheader("Indicator Breakdown")
    rows = []
    for sig in signal.individual_signals:
        rows.append({
            "Indicator": sig.indicator_name,
            "Direction": sig.direction.value,
            "Confidence": f"{sig.confidence:.0%}",
            "Detail": sig.detail,
        })

    st.table(rows)

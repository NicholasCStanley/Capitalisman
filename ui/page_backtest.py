"""Backtest page: historical prediction accuracy evaluation."""

import pandas as pd
import streamlit as st

from backtesting.engine import run_backtest
from charts.factory import render_equity_curve, render_price_chart
from data.fetcher import fetch_ohlcv
from indicators.registry import get_all_indicators
from ui.components import (
    capital_input,
    check_data_sufficiency,
    horizon_input,
    indicator_picker,
    period_select,
    ticker_input,
)


def render():
    st.header("Backtest")

    # Sidebar controls
    with st.sidebar:
        ticker = ticker_input(key="backtest_ticker")
        period = period_select(key="backtest_period", default="1y")
        horizon = horizon_input(key="backtest_horizon")
        selected_indicators = indicator_picker(key="backtest_indicators")
        initial_capital = capital_input(key="backtest_capital")

    if not ticker:
        st.info("Enter a ticker symbol in the sidebar to get started.")
        return

    if not selected_indicators:
        st.warning("Select at least one indicator.")
        return

    # Fetch data
    try:
        with st.spinner("Fetching data..."):
            df = fetch_ohlcv(ticker, period=period)
    except ValueError as e:
        st.error(str(e))
        return

    # Check data sufficiency
    data_warnings = check_data_sufficiency(len(df), selected_indicators)
    if data_warnings:
        st.warning(
            f"Insufficient data for {len(data_warnings)} indicator(s) "
            f"({len(df)} bars available):\n\n" + "\n".join(f"- {w}" for w in data_warnings)
            + "\n\nThese will be excluded from signal generation. Use a longer period."
        )

    # Build selected indicators
    all_indicators = get_all_indicators()
    chosen = {n: all_indicators[n] for n in selected_indicators if n in all_indicators}

    # Run backtest
    with st.spinner("Running backtest..."):
        report = run_backtest(
            df, chosen, ticker=ticker, period=period,
            horizon_days=horizon, initial_capital=initial_capital,
        )

    if report.total_trades == 0:
        st.warning("No trades generated. Try a longer period or different indicators.")
        return

    # Metrics row
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Trades", report.total_trades)
    m2.metric("Win Rate", f"{report.win_rate:.1%}")
    m3.metric("Return", f"{report.cumulative_return:+.1%}")
    m4.metric("Max Drawdown", f"{report.max_drawdown:.1%}")
    m5.metric("Sharpe Ratio", f"{report.sharpe_ratio:.2f}")

    pf_display = "No losses" if report.profit_factor == float("inf") else f"{report.profit_factor:.2f}"
    st.metric("Profit Factor", pf_display)

    # Price chart with prediction markers
    computed_df = df.copy()
    for name, indicator in chosen.items():
        computed_df = indicator.compute(computed_df)

    correct_trades = [t for t in report.trades if t.correct]
    incorrect_trades = [t for t in report.trades if not t.correct]

    markers = []
    if correct_trades:
        markers.append({
            "dates": [t.entry_date.strftime("%Y-%m-%d") if hasattr(t.entry_date, "strftime") else str(t.entry_date)
                      for t in correct_trades],
            "prices": [t.entry_price for t in correct_trades],
            "color": "#4CAF50",
            "symbol": "triangle-up",
            "name": "Correct",
            "size": 8,
        })
    if incorrect_trades:
        markers.append({
            "dates": [t.entry_date.strftime("%Y-%m-%d") if hasattr(t.entry_date, "strftime") else str(t.entry_date)
                      for t in incorrect_trades],
            "prices": [t.entry_price for t in incorrect_trades],
            "color": "#F44336",
            "symbol": "triangle-down",
            "name": "Incorrect",
            "size": 8,
        })

    render_price_chart(
        computed_df,
        title=f"{ticker} — Backtest Results",
        markers=markers,
        height=500,
    )

    # Equity curve
    if not report.equity_curve.empty:
        render_equity_curve(report.equity_curve, title="Equity Curve")

    # Trade log
    with st.expander("Trade Log", expanded=False):
        trade_data = []
        for t in report.trades:
            trade_data.append({
                "Entry Date": t.entry_date.strftime("%Y-%m-%d") if hasattr(t.entry_date, "strftime") else str(t.entry_date),
                "Exit Date": t.exit_date.strftime("%Y-%m-%d") if hasattr(t.exit_date, "strftime") else str(t.exit_date),
                "Direction": t.direction,
                "Entry $": f"{t.entry_price:.2f}",
                "Exit $": f"{t.exit_price:.2f}",
                "P&L": f"{t.pnl_pct:+.2%}",
                "Correct": "Yes" if t.correct else "No",
            })
        st.dataframe(pd.DataFrame(trade_data), use_container_width=True)

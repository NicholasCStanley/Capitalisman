"""Screener page: scan multiple tickers and rank by signal strength."""

import streamlit as st

from config.settings import WATCHLIST_PRESETS
from data.fetcher import fetch_ohlcv, get_asset_info
from indicators.registry import get_all_indicators
from signals.base import SignalDirection
from signals.combiner import combine_signals
from ui.components import horizon_input, indicator_picker


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
    st.header("Screener")

    # Sidebar controls
    with st.sidebar:
        preset_name = st.selectbox(
            "Watchlist",
            options=list(WATCHLIST_PRESETS.keys()),
            key="screener_preset",
        )

        if preset_name == "Custom":
            custom_input = st.text_input(
                "Tickers (comma-separated)",
                placeholder="AAPL, MSFT, GOOGL",
                key="screener_custom",
            )
            tickers = [t.strip().upper() for t in custom_input.split(",") if t.strip()]
        else:
            tickers = WATCHLIST_PRESETS[preset_name]

        if tickers:
            st.caption(f"{len(tickers)} tickers: {', '.join(tickers)}")

        horizon = horizon_input(key="screener_horizon")
        selected_indicators = indicator_picker(key="screener_indicators")

        scan_clicked = st.button("Scan Watchlist", type="primary", use_container_width=True)

    if not tickers:
        st.info("Select a watchlist or enter custom tickers in the sidebar.")
        return

    if not selected_indicators:
        st.warning("Select at least one indicator.")
        return

    # Run scan
    if scan_clicked:
        all_indicators = get_all_indicators()
        chosen = {n: all_indicators[n] for n in selected_indicators if n in all_indicators}

        results = []
        progress = st.progress(0, text="Scanning...")

        for i, ticker in enumerate(tickers):
            progress.progress((i + 1) / len(tickers), text=f"Scanning {ticker}...")
            try:
                df = fetch_ohlcv(ticker, period="6mo")
                computed = df.copy()
                for indicator in chosen.values():
                    computed = indicator.compute(computed)
                signal = combine_signals(chosen, computed, horizon_days=horizon, precomputed=True)

                info = get_asset_info(ticker)
                name = info["name"] if info else ticker
                price = df["Close"].iloc[-1]
                prev_close = df["Close"].iloc[-2] if len(df) > 1 else price
                change_pct = (price - prev_close) / prev_close * 100

                results.append({
                    "ticker": ticker,
                    "name": name,
                    "price": price,
                    "change_pct": change_pct,
                    "direction": signal.direction,
                    "confidence": signal.confidence,
                    "reasoning": signal.reasoning,
                    "scores": signal.scores,
                })
            except Exception:
                continue

        progress.empty()

        if not results:
            st.warning("No results. All tickers failed to fetch or compute.")
            return

        # Sort by confidence descending
        results.sort(key=lambda r: r["confidence"], reverse=True)
        st.session_state["screener_results"] = results

    # Display results
    results = st.session_state.get("screener_results")
    if not results:
        st.info("Click **Scan Watchlist** to analyze tickers.")
        return

    st.markdown(f"**{len(results)} results** — sorted by confidence")

    for i, r in enumerate(results):
        color = _signal_color(r["direction"])
        emoji = _signal_emoji(r["direction"])
        change_color = "#4CAF50" if r["change_pct"] >= 0 else "#F44336"

        col_ticker, col_price, col_signal, col_conf, col_action = st.columns(
            [2, 2, 1.5, 1, 1]
        )

        with col_ticker:
            st.markdown(f"**{r['ticker']}**  \n{r['name']}")

        with col_price:
            st.markdown(
                f"${r['price']:,.2f}  \n"
                f"<span style='color:{change_color}'>{r['change_pct']:+.2f}%</span>",
                unsafe_allow_html=True,
            )

        with col_signal:
            st.markdown(
                f"<span style='color:{color}; font-weight:bold;'>"
                f"{emoji} {r['direction'].value}</span>",
                unsafe_allow_html=True,
            )

        with col_conf:
            st.markdown(f"{r['confidence']:.0%}")

        with col_action:

            def _go_predict(ticker=r["ticker"]):
                st.session_state["predict_ticker"] = ticker
                st.session_state["nav_page"] = "Predict"

            st.button(
                "View",
                key=f"screener_view_{i}",
                on_click=_go_predict,
            )

        with st.expander(f"Reasoning — {r['ticker']}", expanded=False):
            st.write(r["reasoning"])
            scores = r["scores"]
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("BUY", f"{scores.get('BUY', 0):.2f}")
            sc2.metric("SELL", f"{scores.get('SELL', 0):.2f}")
            sc3.metric("HOLD", f"{scores.get('HOLD', 0):.2f}")

        if i < len(results) - 1:
            st.divider()

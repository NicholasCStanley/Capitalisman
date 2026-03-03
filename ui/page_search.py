"""Search page: discover tickers via Yahoo Finance search."""

import streamlit as st

from data.fetcher import search_tickers


def render():
    st.header("Search")
    st.caption("Find ticker symbols by company name, keyword, or symbol.")

    query = st.text_input(
        "Search tickers",
        placeholder="e.g. Apple, Tesla, Bitcoin...",
        key="search_query",
    )

    if not query:
        # Show recent searches if available
        recents = st.session_state.get("recent_searches", [])
        if recents:
            st.markdown("**Recent searches:**")
            cols = st.columns(min(len(recents), 4))
            for i, q in enumerate(recents[:4]):
                if cols[i].button(q, key=f"recent_search_{i}"):
                    st.session_state["search_query"] = q
                    st.rerun()
        else:
            st.info("Type a company name or symbol above to search.")
        return

    # Track recent searches
    recents = st.session_state.get("recent_searches", [])
    if query not in recents:
        recents.insert(0, query)
        st.session_state["recent_searches"] = recents[:8]

    with st.spinner("Searching..."):
        results = search_tickers(query)

    if not results:
        st.warning(f"No results found for '{query}'.")
        return

    st.markdown(f"**{len(results)} result(s)**")

    for i, r in enumerate(results):
        symbol = r["symbol"]
        name = r["name"] or symbol
        exchange = r["exchange"]
        qtype = r["type"]

        col_info, col_btn = st.columns([4, 1])
        with col_info:
            st.markdown(
                f"**{symbol}** — {name}"
                + (f"  \n`{exchange}` | {qtype}" if exchange or qtype else "")
            )
        with col_btn:
            if st.button("Analyze", key=f"analyze_{i}_{symbol}"):
                st.session_state["predict_ticker"] = symbol
                st.session_state["nav_page"] = "Predict"
                st.rerun()

        if i < len(results) - 1:
            st.divider()

"""Plotly candlestick chart with indicator subplots."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_candlestick_chart(
    df: pd.DataFrame,
    title: str = "",
    overlays: list[dict[str, Any]] | None = None,
    subplots: list[dict[str, Any]] | None = None,
    markers: list[dict[str, Any]] | None = None,
    height: int = 800,
) -> go.Figure:
    """Create a multi-pane candlestick chart with Plotly.

    Args:
        df: DataFrame with OHLCV + indicator columns.
        title: Chart title.
        overlays: List of overlay configs (drawn on price pane).
            Each: {'columns': [...], 'colors': {...}}
        subplots: List of subplot configs (separate panes).
            Each: {'columns': [...], 'colors': {...}, 'subplot_title': str}
        markers: List of marker configs for buy/sell/prediction points.
            Each: {'dates': [...], 'prices': [...], 'color': str, 'symbol': str, 'name': str}
        height: Chart height in pixels.

    Returns:
        Plotly Figure.
    """
    overlays = overlays or []
    subplots = subplots or []
    markers = markers or []

    n_subplots = 1 + len(subplots)  # price + indicator subplots
    row_heights = [0.5] + [0.5 / max(len(subplots), 1)] * len(subplots)

    subplot_titles = [title or "Price"] + [s.get("subplot_title", "") for s in subplots]

    fig = make_subplots(
        rows=n_subplots,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
    )

    # Use string dates for x-axis to avoid weekend gaps
    x_dates = df.index.strftime("%Y-%m-%d") if hasattr(df.index, "strftime") else df.index

    # Candlestick on row 1
    fig.add_trace(
        go.Candlestick(
            x=x_dates,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
            increasing_line_color="#26A69A",
            decreasing_line_color="#EF5350",
        ),
        row=1,
        col=1,
    )

    # Overlays on price pane
    for overlay in overlays:
        for col_name in overlay.get("columns", []):
            if col_name in df.columns:
                color = overlay.get("colors", {}).get(col_name, "#888888")
                fig.add_trace(
                    go.Scatter(
                        x=x_dates,
                        y=df[col_name],
                        mode="lines",
                        name=col_name,
                        line=dict(color=color, width=1),
                    ),
                    row=1,
                    col=1,
                )

    # Markers on price pane
    for marker in markers:
        fig.add_trace(
            go.Scatter(
                x=marker["dates"],
                y=marker["prices"],
                mode="markers",
                name=marker.get("name", "Signal"),
                marker=dict(
                    color=marker.get("color", "#FFC107"),
                    symbol=marker.get("symbol", "triangle-up"),
                    size=marker.get("size", 10),
                ),
            ),
            row=1,
            col=1,
        )

    # Indicator subplots
    for i, subplot in enumerate(subplots, start=2):
        for col_name in subplot.get("columns", []):
            if col_name in df.columns:
                color = subplot.get("colors", {}).get(col_name, "#888888")
                # MACD histogram as bar chart
                if "hist" in col_name.lower():
                    colors = [
                        "#26A69A" if v >= 0 else "#EF5350"
                        for v in df[col_name].fillna(0)
                    ]
                    fig.add_trace(
                        go.Bar(
                            x=x_dates,
                            y=df[col_name],
                            name=col_name,
                            marker_color=colors,
                        ),
                        row=i,
                        col=1,
                    )
                else:
                    fig.add_trace(
                        go.Scatter(
                            x=x_dates,
                            y=df[col_name],
                            mode="lines",
                            name=col_name,
                            line=dict(color=color, width=1),
                        ),
                        row=i,
                        col=1,
                    )

    fig.update_layout(
        height=height,
        template="plotly_dark",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_rangeslider_visible=False,
        margin=dict(l=50, r=20, t=60, b=20),
    )

    # Remove rangeslider for all subplots
    fig.update_xaxes(rangeslider_visible=False)

    return fig


def create_equity_curve(
    equity: pd.Series,
    title: str = "Equity Curve",
    height: int = 400,
) -> go.Figure:
    """Create an equity curve chart."""
    fig = go.Figure()

    x_dates = equity.index.strftime("%Y-%m-%d") if hasattr(equity.index, "strftime") else equity.index

    fig.add_trace(
        go.Scatter(
            x=x_dates,
            y=equity.values,
            mode="lines",
            name="Equity",
            line=dict(color="#2196F3", width=2),
            fill="tozeroy",
            fillcolor="rgba(33, 150, 243, 0.1)",
        )
    )

    fig.update_layout(
        title=title,
        height=height,
        template="plotly_dark",
        xaxis_title="Date",
        yaxis_title="Portfolio Value ($)",
        margin=dict(l=50, r=20, t=40, b=40),
    )

    return fig

# Capitalisman

A personal stock and crypto prediction tool that generates BUY/SELL/HOLD signals from technical indicators and backtests prediction accuracy over historical data. Built with Streamlit, yfinance, and TradingView-style charts.

## Features

### Signal Generation
- **9 technical indicators** across 4 categories (trend, momentum, volatility, volume)
- **Weighted majority voting** combines indicator signals into a single BUY/SELL/HOLD prediction with confidence score
- **Timescale-adaptive weighting** — short horizons boost momentum indicators, long horizons boost trend indicators
- Configurable prediction horizons from 1 to 30 days

### Backtesting
- **Walk-forward engine** with no look-ahead bias
- Computes win rate, cumulative return, max drawdown, Sharpe ratio, and profit factor
- Generates equity curve and color-coded prediction accuracy markers on price charts
- Detailed trade log with entry/exit prices and P&L per trade

### Data & Charts
- **yfinance** for reliable OHLCV data (stocks, ETFs, crypto — no API keys needed)
- **Plotly** multi-pane candlestick charts with indicator overlays and subplots
- **TradingView Lightweight Charts** integration (optional, auto-fallback to Plotly)
- In-memory caching with 5-minute TTL

## Technical Indicators

| Category | Indicator | Signal Logic |
|---|---|---|
| Trend | SMA Crossover (20/50) | BUY on golden cross, SELL on death cross |
| Trend | EMA Crossover (12/26) | BUY when short EMA crosses above long EMA |
| Trend | MACD (12,26,9) | BUY when MACD line crosses above signal line |
| Trend | ADX (14) | Confirms trend strength; +DI/-DI determines direction |
| Momentum | RSI (14) | BUY below 30 (oversold), SELL above 70 (overbought) |
| Momentum | Stochastic (14,3,3) | BUY when %K crosses %D below 20; SELL above 80 |
| Volatility | Bollinger Bands (20,2) | BUY at lower band, SELL at upper band |
| Volume | VWAP | BUY above VWAP, SELL below |
| Volume | OBV | BUY on positive divergence from price |

## Pages

### Predict
Enter a ticker and prediction horizon, select indicators, and get a combined signal card with confidence score, score breakdown, multi-pane chart, and per-indicator detail table.

### Backtest
Run walk-forward backtests over historical data. View metrics (win rate, return, drawdown, Sharpe, profit factor), price chart with correct/incorrect prediction markers, equity curve, and full trade log.

### Explore
Browse any ticker with interactive multi-pane charts. Toggle indicator overlays and subplots, view asset info, and inspect raw OHLCV data.

## Installation

```bash
git clone <repository-url>
cd Capitalisman
pip install -r requirements.txt
```

### Requirements

- Python 3.10+
- Dependencies (installed via `requirements.txt`):
  - `streamlit` — dashboard UI
  - `yfinance` — market data
  - `ta` — technical indicator computations
  - `plotly` — interactive charting
  - `pandas`, `numpy` — data manipulation
  - `lightweight-charts` — TradingView-style charts (optional, Plotly fallback is automatic)

## Usage

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`. Use the sidebar to navigate between pages and configure inputs.

### Quick Start

1. **Predict** — Enter `AAPL`, set a 5-day horizon, leave all indicators selected, and view the signal
2. **Backtest** — Enter `AAPL`, select 1-year period with 5-day horizon, and review performance metrics
3. **Explore** — Enter `BTC-USD`, toggle different indicators on/off, and browse the charts

### Supported Tickers

Any ticker supported by Yahoo Finance:
- **Stocks**: `AAPL`, `GOOGL`, `MSFT`, `TSLA`, etc.
- **ETFs**: `SPY`, `QQQ`, `VTI`, etc.
- **Crypto**: `BTC-USD`, `ETH-USD`, `SOL-USD`, etc.
- **Indices**: `^GSPC` (S&P 500), `^DJI` (Dow Jones), etc.

## Project Structure

```
Capitalisman/
├── app.py                      # Streamlit entry point
├── requirements.txt
├── config/
│   └── settings.py             # Constants, weights, thresholds
├── data/
│   └── fetcher.py              # yfinance wrapper with caching
├── indicators/
│   ├── base.py                 # BaseIndicator ABC
│   ├── registry.py             # Auto-registration decorator
│   ├── trend.py                # SMA, EMA, MACD, ADX
│   ├── momentum.py             # RSI, Stochastic
│   ├── volatility.py           # Bollinger Bands
│   └── volume.py               # VWAP, OBV
├── signals/
│   ├── base.py                 # SignalDirection, SignalResult, CombinedSignal
│   └── combiner.py             # Weighted majority voting
├── backtesting/
│   ├── engine.py               # Walk-forward backtest loop
│   ├── metrics.py              # Performance metric computation
│   └── report.py               # BacktestReport dataclass
├── charts/
│   ├── tradingview.py          # TradingView Lightweight Charts
│   ├── plotly_fallback.py      # Plotly candlestick + subplots
│   └── factory.py              # Auto-selects chart renderer
└── ui/
    ├── components.py           # Shared sidebar widgets
    ├── page_predict.py         # Signal generation page
    ├── page_backtest.py        # Backtesting page
    └── page_explore.py         # Data exploration page
```

## How Signal Combination Works

1. Each indicator produces a direction (BUY/SELL/HOLD) and confidence (0.0–1.0)
2. Confidence is scaled by distance from thresholds (e.g., RSI at 20 has higher confidence than RSI at 29)
3. Each signal's score = confidence × indicator weight × timescale adjustment
4. Scores are summed per direction; the highest-scoring direction wins
5. If the top two directions are within 10% of each other, the result is HOLD (ambiguous signal)

## Configuration

All defaults are in `config/settings.py`:

- **Indicator parameters** — periods, thresholds (RSI overbought/oversold, Stochastic zones, etc.)
- **Indicator weights** — base importance of each indicator in signal combination
- **Timescale adjustments** — how weights shift based on prediction horizon (short/medium/long)
- **Ambiguity threshold** — minimum margin between top two signals to avoid HOLD

## Disclaimer

This tool is for educational and personal research purposes only. It is not financial advice. Past performance of backtested strategies does not guarantee future results. Always do your own research before making investment decisions.

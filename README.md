# Capitalisman

<p align="center">
  <img src="Capitalisman.png" alt="Capitalisman" width="400">
</p>

A personal stock and crypto prediction tool that helps you make more informed trading decisions. It analyzes price data using proven technical indicators, combines their signals into a single BUY/SELL/HOLD recommendation with a confidence score, and lets you test how well those predictions would have performed on real historical data — all through an easy-to-use web dashboard.

No API keys, no account signups, and no trading experience required to get started.

## What It Does

### Predict — Get a Signal for Any Stock or Crypto

Pick a ticker (like `AAPL` for Apple, or `BTC-USD` for Bitcoin) and a time horizon (how many days ahead you want to predict). The tool runs 9 different technical analyses on the price data and combines them into one clear recommendation:

- **BUY** — indicators suggest the price is likely to go up
- **SELL** — indicators suggest the price is likely to go down
- **HOLD** — signals are mixed or too close to call

Each prediction comes with a **confidence score** (0–100%) so you can see how strongly the indicators agree, plus a full breakdown showing what each individual indicator is saying and why.

### Backtest — Test How Well Predictions Would Have Worked

Before trusting any strategy, you want to know: "How accurate would this have been in the past?" The backtest page answers that question by running predictions across historical data and measuring the results.

You'll see:

- **Win Rate** — what percentage of predictions were correct
- **Total Return** — how much money you would have made or lost
- **Max Drawdown** — the worst peak-to-valley decline (how much pain you'd have endured)
- **Sharpe Ratio** — return relative to risk (higher is better; above 1.0 is generally good)
- **Profit Factor** — total gains divided by total losses (above 1.0 means profitable)
- **Equity Curve** — a chart showing your portfolio value over time
- **Trade Log** — every individual trade with entry/exit prices and profit/loss

Backtests include **configurable transaction costs** (slippage and commissions, default 0.1% per trade) so results reflect realistic trading conditions rather than idealized zero-cost scenarios.

### Explore — Browse Charts and Data

An interactive charting page where you can look at any stock or crypto with professional-style candlestick charts. Toggle different indicator overlays on and off, view company information, and inspect the raw price data.

## Getting Started

### Installation

You'll need Python 3.10 or newer installed on your computer.

```bash
git clone <repository-url>
cd Capitalisman
pip install -r requirements.txt
```

### Running the App

```bash
streamlit run app.py
```

This opens the dashboard in your web browser at `http://localhost:8501`. Use the sidebar on the left to switch between pages and adjust settings.

### Quick Start

1. **Try a prediction** — The app starts on the Predict page. Type `AAPL` as the ticker, set the horizon to 5 days, and click through. You'll see a BUY/SELL/HOLD signal with a confidence score and a detailed chart.

2. **Run a backtest** — Switch to the Backtest page in the sidebar. Type `AAPL`, pick "1y" (one year) as the period, and keep the 5-day horizon. You'll see how accurate the predictions would have been over the past year.

3. **Explore a chart** — Switch to the Explore page. Try `BTC-USD` (Bitcoin) and toggle different indicators on and off to see how they overlay on the price chart.

### What Tickers Can I Use?

Anything available on Yahoo Finance:

- **Stocks** — `AAPL` (Apple), `GOOGL` (Google), `MSFT` (Microsoft), `TSLA` (Tesla), etc.
- **ETFs** — `SPY` (S&P 500 ETF), `QQQ` (Nasdaq 100 ETF), `VTI` (Total Market ETF), etc.
- **Crypto** — `BTC-USD` (Bitcoin), `ETH-USD` (Ethereum), `SOL-USD` (Solana), etc.
- **Indices** — `^GSPC` (S&P 500), `^DJI` (Dow Jones), etc.

## Technical Indicators

The tool uses 9 indicators across 4 categories. Each one looks at a different aspect of price behavior:

### Trend Indicators — "Which direction is the price moving?"

| Indicator | What It Does |
|---|---|
| **SMA Crossover** (20/50) | Compares a short-term average (20 days) to a long-term average (50 days). When the short average crosses above the long one ("golden cross"), it's a BUY signal. The reverse ("death cross") is a SELL signal. |
| **EMA Crossover** (12/26) | Similar to SMA but uses exponential moving averages, which react faster to recent price changes. |
| **MACD** (12, 26, 9) | Measures the momentum of trend changes. A BUY signal occurs when the MACD line crosses above its signal line, suggesting upward momentum is building. |
| **ADX** (14) | Measures how strong the current trend is (regardless of direction). When the trend is strong, it looks at directional indicators (+DI/-DI) to determine whether it's bullish or bearish. |

### Momentum Indicators — "Is the price moving too fast?"

| Indicator | What It Does |
|---|---|
| **RSI** (14) | Measures whether an asset is "oversold" (below 30 — potentially undervalued, BUY signal) or "overbought" (above 70 — potentially overvalued, SELL signal). |
| **Stochastic** (14, 3, 3) | Similar to RSI but compares the closing price to its recent range. Signals occur when the fast line (%K) crosses the slow line (%D) in extreme zones (below 20 or above 80). |

### Volatility Indicators — "How wild are the price swings?"

| Indicator | What It Does |
|---|---|
| **Bollinger Bands** (20, 2) | Creates upper and lower bands around the price based on volatility. When the price touches the lower band, it may be oversold (BUY). When it touches the upper band, it may be overbought (SELL). |

### Volume Indicators — "Is the trading volume confirming the price movement?"

| Indicator | What It Does |
|---|---|
| **VWAP** (20-day rolling) | Volume-Weighted Average Price — the average price weighted by how much was traded at each level over a rolling 20-day window. Price above VWAP suggests bullish sentiment; below suggests bearish. |
| **OBV** | On-Balance Volume — tracks cumulative volume flow. If the price is falling but volume is rising (positive divergence), it may signal an upcoming reversal (BUY). |

## How Predictions Work

The tool doesn't rely on any single indicator. Instead, it combines all selected indicators using a weighted voting system:

1. **Each indicator votes independently** — it produces a direction (BUY, SELL, or HOLD) and a confidence level (0–100%) based on how far the current reading is from key thresholds.

2. **Votes are weighted** — some indicators carry more weight than others. For example, MACD (weight 1.2) has slightly more influence than OBV (weight 0.7).

3. **Weights adapt to your time horizon** — if you're predicting 1–3 days ahead, momentum indicators (RSI, Stochastic) get boosted because they're better at short-term signals. For predictions beyond 10 days, trend indicators (SMA, EMA, MACD) get boosted instead.

4. **Only BUY and SELL compete** — indicators that vote HOLD are recorded but don't influence the directional outcome. The direction with the highest weighted score wins.

5. **Ambiguous signals become HOLD** — if BUY and SELL scores are within 10% of each other, the result is HOLD rather than making a low-confidence call.

## Backtest Settings

When running a backtest, you can configure:

- **Ticker** — which stock or crypto to test
- **Period** — how far back to test (1 month to max available history)
- **Prediction Horizon** — how many days ahead each prediction targets (1–30 days)
- **Indicators** — which indicators to include in the signal
- **Initial Capital** — starting portfolio value (default $10,000)
- **Transaction Cost** — round-trip cost per trade as a percentage (default 0.1%), covering slippage and commissions

## Configuration

Advanced users can adjust defaults in `config/settings.py`:

- **Indicator parameters** — periods, thresholds (RSI overbought/oversold levels, Stochastic zones, Bollinger Band width, etc.)
- **Indicator weights** — how much influence each indicator has in the combined signal
- **Timescale adjustments** — how weights shift for short, medium, and long prediction horizons
- **Ambiguity threshold** — how close BUY and SELL scores need to be before the result becomes HOLD (default 10%)
- **Transaction cost** — default round-trip cost percentage for backtests

## Project Structure

```
Capitalisman/
├── app.py                      # App entry point
├── requirements.txt            # Python dependencies
├── config/
│   └── settings.py             # All configurable defaults
├── data/
│   └── fetcher.py              # Market data fetching with caching
├── indicators/
│   ├── base.py                 # Indicator interface
│   ├── registry.py             # Auto-registration system
│   ├── trend.py                # SMA, EMA, MACD, ADX
│   ├── momentum.py             # RSI, Stochastic
│   ├── volatility.py           # Bollinger Bands
│   └── volume.py               # VWAP, OBV
├── signals/
│   ├── base.py                 # Signal data types
│   └── combiner.py             # Weighted voting combiner
├── backtesting/
│   ├── engine.py               # Walk-forward backtest engine
│   ├── metrics.py              # Performance metric calculations
│   └── report.py               # Backtest results structure
├── charts/
│   ├── tradingview.py          # TradingView chart rendering
│   ├── plotly_fallback.py      # Plotly chart rendering
│   └── factory.py              # Auto-selects best chart renderer
└── ui/
    ├── components.py           # Shared sidebar controls
    ├── page_predict.py         # Predict page
    ├── page_backtest.py        # Backtest page
    └── page_explore.py         # Explore page
```

## Dependencies

Installed automatically via `pip install -r requirements.txt`:

| Package | Purpose |
|---|---|
| `streamlit` | Web dashboard framework |
| `yfinance` | Free market data from Yahoo Finance |
| `ta` | Technical indicator calculations |
| `plotly` | Interactive charts |
| `pandas` / `numpy` | Data processing |
| `lightweight-charts` | TradingView-style charts (optional — the app automatically falls back to Plotly if not installed) |

## Disclaimer

This tool is for **educational and personal research purposes only**. It is not financial advice. Technical indicators are backward-looking tools that analyze past price patterns — they cannot predict the future with certainty. Past performance of backtested strategies does not guarantee future results. Always do your own research before making investment decisions.

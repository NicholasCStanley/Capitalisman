"""Application constants and default configuration."""

# Data fetching defaults
DEFAULT_PERIOD = "1y"
DEFAULT_INTERVAL = "1d"
CACHE_TTL_SECONDS = 300  # 5 minutes

# Prediction defaults
DEFAULT_PREDICTION_HORIZON = 5  # days

# Backtesting defaults
DEFAULT_BACKTEST_PERIOD = "6mo"
DEFAULT_INITIAL_CAPITAL = 10_000.0
DEFAULT_COST_PER_TRADE_PCT = 0.1  # round-trip transaction cost as % (slippage + commission)
WARMUP_BUFFER = 50  # extra bars beyond longest indicator lookback

# Indicator parameters
SMA_SHORT = 20
SMA_LONG = 50
EMA_SHORT = 12
EMA_LONG = 26
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
ADX_PERIOD = 14
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
STOCH_K = 14
STOCH_D = 3
STOCH_SMOOTH = 3
STOCH_OVERSOLD = 20
STOCH_OVERBOUGHT = 80
BB_PERIOD = 20
BB_STD = 2

# Indicator weights for signal combination
INDICATOR_WEIGHTS = {
    "SMA Crossover": 1.0,
    "EMA Crossover": 1.0,
    "MACD": 1.2,
    "ADX": 0.8,
    "RSI": 1.1,
    "Stochastic": 1.0,
    "Bollinger Bands": 0.9,
    "VWAP": 0.8,
    "OBV": 0.7,
}

# Timescale weight adjustments
# Multiplied with base weights depending on prediction horizon
TIMESCALE_ADJUSTMENTS = {
    "short": {  # <= 3 days
        "trend": 0.7,
        "momentum": 1.4,
        "volatility": 1.2,
        "volume": 1.0,
    },
    "medium": {  # 4-10 days
        "trend": 1.0,
        "momentum": 1.0,
        "volatility": 1.0,
        "volume": 1.0,
    },
    "long": {  # > 10 days
        "trend": 1.4,
        "momentum": 0.7,
        "volatility": 0.8,
        "volume": 1.0,
    },
}

# Indicator category mapping
INDICATOR_CATEGORIES = {
    "SMA Crossover": "trend",
    "EMA Crossover": "trend",
    "MACD": "trend",
    "ADX": "trend",
    "RSI": "momentum",
    "Stochastic": "momentum",
    "Bollinger Bands": "volatility",
    "VWAP": "volume",
    "OBV": "volume",
}

# Signal combination
AMBIGUITY_THRESHOLD = 0.10  # if top two directions within 10%, result is HOLD

# Tunable thresholds exposed in the UI's "Advanced Settings" panel.
# Each entry maps a setting name to metadata for rendering a slider.
TUNABLE_THRESHOLDS = {
    "RSI_OVERSOLD": {"label": "RSI Oversold", "min": 10, "max": 50, "step": 1},
    "RSI_OVERBOUGHT": {"label": "RSI Overbought", "min": 50, "max": 90, "step": 1},
    "STOCH_OVERSOLD": {"label": "Stochastic Oversold", "min": 5, "max": 40, "step": 1},
    "STOCH_OVERBOUGHT": {"label": "Stochastic Overbought", "min": 60, "max": 95, "step": 1},
    "AMBIGUITY_THRESHOLD": {"label": "Ambiguity Threshold", "min": 0.0, "max": 0.30, "step": 0.01},
}

# Available data periods and intervals for UI
PERIODS = ["1d", "5d", "1wk", "2wk", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]
INTERVALS = ["1m", "5m", "15m", "1h", "1d", "1wk", "1mo"]

# Friendly display labels for period selector
PERIOD_LABELS = {
    "1d": "1 Day",
    "5d": "5 Days",
    "1wk": "1 Week",
    "2wk": "2 Weeks",
    "1mo": "1 Month",
    "3mo": "3 Months",
    "6mo": "6 Months",
    "1y": "1 Year",
    "2y": "2 Years",
    "5y": "5 Years",
    "max": "Max",
}

# Maps short user-facing periods to longer yfinance fetch periods for indicator warmup.
# Periods not listed here are fetched as-is (they already have enough data).
WARMUP_FETCH_PERIOD = {
    "1d": "3mo",
    "5d": "3mo",
    "1wk": "3mo",
    "2wk": "3mo",
    "1mo": "6mo",
    "3mo": "1y",
}

# Maps short periods to longer fetch periods for backtesting.
# The backtest engine requires max_lookback + WARMUP_BUFFER + horizon bars,
# so we need more history than the charting warmup provides.
BACKTEST_FETCH_PERIOD = {
    "1d": "1y",
    "5d": "1y",
    "1wk": "1y",
    "2wk": "1y",
    "1mo": "1y",
    "3mo": "1y",
}

# Calendar days to keep when trimming warmup data back to display range.
# Only needed for periods that appear in WARMUP_FETCH_PERIOD.
PERIOD_CALENDAR_DAYS = {
    "1d": 1,
    "5d": 5,
    "1wk": 7,
    "2wk": 14,
    "1mo": 31,
    "3mo": 93,
}

# Yahoo Finance intraday data limits (max history available per interval)
INTRADAY_MAX_PERIODS = {
    "1m": "7d",
    "5m": "60d",
    "15m": "60d",
    "1h": "730d",
}
INTRADAY_WARNINGS = {
    "1m": "1-minute data is limited to the last 7 days regardless of period selected.",
    "5m": "5-minute data is limited to the last 60 days regardless of period selected.",
    "15m": "15-minute data is limited to the last 60 days regardless of period selected.",
    "1h": "Hourly data is limited to the last 730 days regardless of period selected.",
}

# Watchlist presets for screener
WATCHLIST_PRESETS = {
    "Tech Giants": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"],
    "S&P 500 Top 10": ["AAPL", "MSFT", "GOOGL", "AMZN", "BRK-B", "UNH", "JNJ", "XOM", "JPM", "V"],
    "Major Crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "XRP-USD", "DOGE-USD", "DOT-USD", "AVAX-USD"],
    "Indices": ["^GSPC", "^DJI", "^IXIC", "^RUT"],
    "Custom": [],
}

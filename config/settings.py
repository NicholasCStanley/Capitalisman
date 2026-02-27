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

# Available data periods and intervals for UI
PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]
INTERVALS = ["1m", "5m", "15m", "1h", "1d", "1wk", "1mo"]

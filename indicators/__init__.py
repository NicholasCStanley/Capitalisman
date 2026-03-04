"""Auto-import all indicator modules to trigger registration."""

from indicators import trend, momentum, volatility, volume  # noqa: F401
from indicators import macro, structural, microstructure, systemic  # noqa: F401

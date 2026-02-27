"""Signal data types."""

from dataclasses import dataclass, field
from enum import Enum


class SignalDirection(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class SignalResult:
    """Result from a single indicator."""

    indicator_name: str
    direction: SignalDirection
    confidence: float  # 0.0 to 1.0
    detail: str = ""  # human-readable explanation

    def __post_init__(self):
        self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class CombinedSignal:
    """Result of combining multiple indicator signals."""

    direction: SignalDirection
    confidence: float
    scores: dict[str, float] = field(default_factory=dict)  # direction -> weighted score
    individual_signals: list[SignalResult] = field(default_factory=list)
    reasoning: str = ""

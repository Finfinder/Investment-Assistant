"""Weighted scoring system for signal aggregation."""

from app.core.models import Direction
from app.modules.signal_aggregation.aggregator import SignalAggregator

DEFAULT_WEIGHTS: dict[str, float] = {
    "technical_analysis": 0.5,
    "patterns": 0.3,
    "fundamental": 0.2,
}

# Score thresholds for direction classification
BULLISH_THRESHOLD = 0.15
BEARISH_THRESHOLD = -0.15


def calculate_weighted_score(
    aggregator: SignalAggregator,
    weights: dict[str, float] | None = None,
) -> float:
    """Calculate weighted score from all signal sources.

    Returns a value between -1.0 (strong bearish) and +1.0 (strong bullish).
    """
    w = weights or DEFAULT_WEIGHTS
    signals = aggregator.get_all_signals()

    weighted_sum = 0.0
    total_weight = 0.0
    for source, score in signals.items():
        source_weight = w.get(source, 0.0)
        weighted_sum += score * source_weight
        total_weight += source_weight

    if total_weight == 0.0:
        return 0.0
    return max(-1.0, min(1.0, weighted_sum / total_weight))


def determine_direction(score: float) -> Direction | None:
    """Determine overall trade direction from weighted score.

    Returns LONG for bullish, SHORT for bearish, None for neutral.
    """
    if score >= BULLISH_THRESHOLD:
        return Direction.LONG
    if score <= BEARISH_THRESHOLD:
        return Direction.SHORT
    return None

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

# Tolerance for treating an accumulated float weight as effectively zero.
# Floating-point cancellation (e.g. 0.3 - 0.1 - 0.2) may not equal exactly 0.0, so the
# zero-weight guard must detect "near zero" rather than an exact literal.
_FLOAT_ZERO_EPSILON = 1e-9


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

    if abs(total_weight) < _FLOAT_ZERO_EPSILON:
        return 0.0
    return max(-1.0, min(1.0, weighted_sum / total_weight))


def determine_direction(
    score: float,
    bullish_threshold: float | None = None,
    bearish_threshold: float | None = None,
) -> Direction | None:
    """Determine overall trade direction from weighted score.

    Returns LONG for bullish, SHORT for bearish, None for neutral.

    Args:
        score: Weighted score between -1.0 (bearish) and +1.0 (bullish).
        bullish_threshold: Custom LONG threshold. Defaults to BULLISH_THRESHOLD (0.15).
            Score >= threshold results in Direction.LONG.
        bearish_threshold: Custom SHORT threshold. Defaults to BEARISH_THRESHOLD (-0.15).
            Score <= threshold results in Direction.SHORT.
    """
    b_thresh = bullish_threshold if bullish_threshold is not None else BULLISH_THRESHOLD
    s_thresh = bearish_threshold if bearish_threshold is not None else BEARISH_THRESHOLD

    if score >= b_thresh:
        return Direction.LONG
    if score <= s_thresh:
        return Direction.SHORT
    return None

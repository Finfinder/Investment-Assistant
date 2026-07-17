"""Confidence scorer — rates scenario certainty from 0% to 100%."""

from app.core.models import (
    RELIABILITY_MULTIPLIER,
    Direction,
    FundamentalData,
    IndicatorValue,
    PatternDetection,
    SignalSummary,
    SignalType,
)

# Mapping of SignalType alignment per direction
_BULLISH_SIGNALS = {SignalType.BUY, SignalType.STRONG_BUY}
_BEARISH_SIGNALS = {SignalType.SELL, SignalType.STRONG_SELL}
_FLOAT_ZERO_EPSILON = 1e-9


def calculate_confidence(
    direction: Direction,
    indicators: list[IndicatorValue] | None = None,
    signal_summary: SignalSummary | None = None,
    patterns: list[PatternDetection] | None = None,
    fundamental: FundamentalData | None = None,
) -> float:
    """Calculate confidence percentage (0-100) for the given direction.

    Factors:
    1. % of TA indicators agreeing with direction (weight 40%)
    2. Pattern confirmation in the same direction (weight 25%)
    3. Fundamental alignment (weight 15%)
    4. ADX trend strength (weight 20%)
    """
    scores: list[tuple[float, float]] = []  # (score 0..1, weight)

    # Factor 1: TA indicator agreement
    ta_score = _ta_agreement(direction, indicators or [], signal_summary)
    scores.append((ta_score, 0.40))

    # Factor 2: Pattern confirmation
    pattern_score = _pattern_confirmation(direction, patterns or [])
    scores.append((pattern_score, 0.25))

    # Factor 3: Fundamental alignment
    fund_score = _fundamental_alignment(direction, fundamental)
    scores.append((fund_score, 0.15))

    # Factor 4: ADX trend strength
    adx_score = _adx_strength(indicators or [])
    scores.append((adx_score, 0.20))

    weighted_sum = sum(s * w for s, w in scores)
    total_weight = sum(w for _, w in scores)

    if abs(total_weight) < _FLOAT_ZERO_EPSILON:
        return 0.0
    return round(min(100.0, max(0.0, (weighted_sum / total_weight) * 100)), 1)


def _ta_agreement(
    direction: Direction,
    indicators: list[IndicatorValue],
    signal_summary: SignalSummary | None,
) -> float:
    """Return ratio of TA indicators agreeing with direction (0..1)."""
    if signal_summary:
        total = (
            signal_summary.overall_buy_count + signal_summary.overall_sell_count + signal_summary.overall_neutral_count
        )
        if total == 0:
            return 0.0
        if direction == Direction.LONG:
            return signal_summary.overall_buy_count / total
        return signal_summary.overall_sell_count / total

    if not indicators:
        return 0.0

    aligned_signals = _BULLISH_SIGNALS if direction == Direction.LONG else _BEARISH_SIGNALS
    agreeing = sum(1 for ind in indicators if ind.signal in aligned_signals)
    return agreeing / len(indicators)


def _pattern_strength(pattern: PatternDetection) -> float:
    """Return the contextual strength of a pattern (0.0..1.0).

    Uses relevance_score as the primary measure when it has been computed
    (value > 0.0). Falls back to confidence when relevance_score equals
    the default 0.0, preserving expected behaviour for manually created
    PatternDetection objects and for patterns that bypassed score_patterns().
    """
    return pattern.relevance_score if pattern.relevance_score > 0.0 else pattern.confidence


def _pattern_confirmation(direction: Direction, patterns: list[PatternDetection]) -> float:
    """Return pattern confirmation score (0..1).

    Uses relevance_score (or confidence as fallback) as the primary strength.
    Each pattern contributes positively if it confirms the direction (bullish
    for LONG, bearish for SHORT) or negatively if it opposes it. The signed
    sum is normalized by the sum of maximum possible weights (all strength=1.0),
    accounting for reliability multipliers. The result is clamped to 0.0..1.0
    so that strong opposing patterns reduce confidence appropriately.

    Formacje z wyższym relevance_score mają większy wpływ na score.
    Formacje z wyższym reliability mają większy wpływ na score
    (mnożnik: ★=1.0, ★★=1.3, ★★★=1.6).
    """
    if not patterns:
        return 0.0

    signed_sum = 0.0
    total_max_weight = 0.0

    for pattern in patterns:
        direction_alignment = 1.0 if pattern.bullish == (direction == Direction.LONG) else -1.0
        strength = _pattern_strength(pattern)
        multiplier = RELIABILITY_MULTIPLIER.get(pattern.reliability, 1.0)
        effective_weight = strength * multiplier
        signed_sum += direction_alignment * effective_weight
        total_max_weight += multiplier

    if total_max_weight < _FLOAT_ZERO_EPSILON:
        return 0.0

    # Normalize by maximum possible weight and clamp to [0.0, 1.0]
    normalized = signed_sum / total_max_weight
    return max(0.0, min(1.0, normalized))


def _fundamental_alignment(direction: Direction, fundamental: FundamentalData | None) -> float:
    """Return fundamental alignment score (0..1)."""
    if fundamental is None:
        return 0.5  # Neutral when no data

    score = fundamental.score  # -100..+100
    if direction == Direction.LONG:
        return max(0.0, min(1.0, (score + 100) / 200))
    return max(0.0, min(1.0, (-score + 100) / 200))


def _adx_strength(indicators: list[IndicatorValue]) -> float:
    """Return ADX-based trend strength score (0..1)."""
    for ind in indicators:
        if ind.name.startswith("ADX") and ind.value is not None:
            # ADX 0-100; >25 indicates trending, >50 strong trend
            return min(1.0, ind.value / 50.0)
    return 0.5  # Neutral if ADX not available

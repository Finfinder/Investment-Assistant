"""Confidence scorer — rates scenario certainty from 0% to 100%."""

from app.core.models import (
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

    if total_weight == 0:
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


def _pattern_confirmation(direction: Direction, patterns: list[PatternDetection]) -> float:
    """Return pattern confirmation score (0..1)."""
    if not patterns:
        return 0.0

    confirming = [p for p in patterns if p.bullish == (direction == Direction.LONG)]
    if not confirming:
        return 0.0

    avg_confidence = sum(p.confidence for p in confirming) / len(confirming)
    ratio = len(confirming) / len(patterns)
    return avg_confidence * ratio


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

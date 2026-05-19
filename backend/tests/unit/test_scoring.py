"""Tests for signal_aggregation/scoring.py"""

from app.core.models import (
    Direction,
    FundamentalData,
    IndicatorValue,
    InstrumentType,
    PatternDetection,
    SignalType,
)
from app.modules.signal_aggregation.aggregator import SignalAggregator
from app.modules.signal_aggregation.scoring import (
    BEARISH_THRESHOLD,
    BULLISH_THRESHOLD,
    calculate_weighted_score,
    determine_direction,
)


def _make_aggregator(ta_signal=SignalType.NEUTRAL, pattern_bullish=True, fund_score=0.0):
    indicators = [IndicatorValue(name="RSI", value=50, signal=ta_signal)]
    patterns = [PatternDetection(pattern_type="Test", confidence=0.8, bullish=pattern_bullish)]
    fundamental = FundamentalData(instrument_type=InstrumentType.FOREX, score=fund_score)
    return SignalAggregator(indicators=indicators, patterns=patterns, fundamental=fundamental)


def test_ta_and_patterns_agree_bullish():
    """TA + patterns both bullish → positive score, LONG direction."""
    agg = _make_aggregator(ta_signal=SignalType.BUY, pattern_bullish=True, fund_score=50)
    score = calculate_weighted_score(agg)
    assert score > BULLISH_THRESHOLD
    assert determine_direction(score) == Direction.LONG


def test_ta_and_patterns_agree_bearish():
    """TA + patterns both bearish → negative score, SHORT direction."""
    agg = _make_aggregator(ta_signal=SignalType.SELL, pattern_bullish=False, fund_score=-50)
    score = calculate_weighted_score(agg)
    assert score < BEARISH_THRESHOLD
    assert determine_direction(score) == Direction.SHORT


def test_ta_and_patterns_disagree():
    """TA bullish + patterns bearish → score closer to 0."""
    agg = _make_aggregator(ta_signal=SignalType.BUY, pattern_bullish=False, fund_score=0)
    score = calculate_weighted_score(agg)
    # Score should be moderated (TA says buy, patterns say bearish)
    assert -0.5 < score < 0.5


def test_fundamental_confirming():
    """Strong fundamental score confirms direction."""
    agg = _make_aggregator(ta_signal=SignalType.BUY, pattern_bullish=True, fund_score=80)
    score_confirmed = calculate_weighted_score(agg)

    agg2 = _make_aggregator(ta_signal=SignalType.BUY, pattern_bullish=True, fund_score=-80)
    score_denied = calculate_weighted_score(agg2)

    # Confirmed should be more bullish than denied
    assert score_confirmed > score_denied


def test_determine_direction_neutral():
    """Score near zero → neutral (None)."""
    assert determine_direction(0.0) is None
    assert determine_direction(0.10) is None
    assert determine_direction(-0.10) is None


def test_determine_direction_thresholds():
    """Exact threshold values."""
    assert determine_direction(BULLISH_THRESHOLD) == Direction.LONG
    assert determine_direction(BEARISH_THRESHOLD) == Direction.SHORT


def test_custom_weights():
    """Custom weights override defaults."""
    agg = _make_aggregator(ta_signal=SignalType.STRONG_BUY, pattern_bullish=False, fund_score=-100)
    # All weight on TA → bullish
    score = calculate_weighted_score(agg, weights={"technical_analysis": 1.0, "patterns": 0.0, "fundamental": 0.0})
    assert score > 0


def test_empty_aggregator():
    """Empty aggregator → score 0, direction None."""
    agg = SignalAggregator()
    score = calculate_weighted_score(agg)
    assert score == 0.0
    assert determine_direction(score) is None


def test_high_relevance_pattern_shifts_weighted_score():
    """Wyższy relevance_score byczej formacji przesuwa wynik w kierunku LONG przy konflikcie kierunków."""
    indicators = [IndicatorValue(name="RSI", value=50, signal=SignalType.NEUTRAL)]
    fundamental = FundamentalData(instrument_type=InstrumentType.FOREX, score=0.0)

    # Bycza (0.9) dominuje nad niedźwiedzią (0.2) → wynik pattern > 0 → score > 0
    patterns_bull_dominant = [
        PatternDetection(pattern_type="Engulfing", confidence=0.8, bullish=True, relevance_score=0.9),
        PatternDetection(pattern_type="ShootingStar", confidence=0.8, bullish=False, relevance_score=0.2),
    ]
    # Niedźwiedzia (0.9) dominuje nad byczą (0.2) → wynik pattern < 0 → score < 0
    patterns_bear_dominant = [
        PatternDetection(pattern_type="Engulfing", confidence=0.8, bullish=True, relevance_score=0.2),
        PatternDetection(pattern_type="ShootingStar", confidence=0.8, bullish=False, relevance_score=0.9),
    ]

    score_bull = calculate_weighted_score(
        SignalAggregator(indicators=indicators, patterns=patterns_bull_dominant, fundamental=fundamental)
    )
    score_bear = calculate_weighted_score(
        SignalAggregator(indicators=indicators, patterns=patterns_bear_dominant, fundamental=fundamental)
    )

    assert score_bull > 0, f"Bull-dominant relevance_score should produce positive score, got {score_bull}"
    assert score_bear < 0, f"Bear-dominant relevance_score should produce negative score, got {score_bear}"
    assert score_bull > score_bear, "Bull-dominant should score higher than bear-dominant"

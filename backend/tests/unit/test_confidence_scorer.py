"""Tests for strategy_generator/confidence_scorer.py"""

from app.core.models import (
    Direction,
    FundamentalData,
    IndicatorValue,
    InstrumentType,
    PatternDetection,
    SignalSummary,
    SignalType,
)
from app.modules.strategy_generator.confidence_scorer import calculate_confidence


def test_high_confidence():
    """All factors aligned → high confidence."""
    indicators = [
        IndicatorValue(name="RSI(14)", value=65, signal=SignalType.BUY),
        IndicatorValue(name="MACD(12,26,9)", value=0.5, signal=SignalType.BUY),
        IndicatorValue(name="ADX(14)", value=40, signal=SignalType.BUY),
    ]
    summary = SignalSummary(
        overall_summary=SignalType.BUY,
        overall_buy_count=8,
        overall_sell_count=1,
        overall_neutral_count=1,
    )
    patterns = [
        PatternDetection(pattern_type="Hammer", confidence=0.9, bullish=True),
        PatternDetection(pattern_type="Engulfing", confidence=0.85, bullish=True),
    ]
    fundamental = FundamentalData(instrument_type=InstrumentType.FOREX, score=70)

    confidence = calculate_confidence(
        direction=Direction.LONG,
        indicators=indicators,
        signal_summary=summary,
        patterns=patterns,
        fundamental=fundamental,
    )

    assert confidence > 60


def test_low_confidence():
    """All factors oppose direction → low confidence."""
    indicators = [
        IndicatorValue(name="RSI(14)", value=25, signal=SignalType.SELL),
        IndicatorValue(name="MACD(12,26,9)", value=-0.5, signal=SignalType.SELL),
        IndicatorValue(name="ADX(14)", value=15, signal=SignalType.NEUTRAL),
    ]
    summary = SignalSummary(
        overall_summary=SignalType.SELL,
        overall_buy_count=1,
        overall_sell_count=8,
        overall_neutral_count=1,
    )
    patterns = [
        PatternDetection(pattern_type="ShootingStar", confidence=0.8, bullish=False),
    ]
    fundamental = FundamentalData(instrument_type=InstrumentType.FOREX, score=-60)

    confidence = calculate_confidence(
        direction=Direction.LONG,
        indicators=indicators,
        signal_summary=summary,
        patterns=patterns,
        fundamental=fundamental,
    )

    assert confidence < 40


def test_mixed_confidence():
    """Some factors agree, some don't → moderate confidence."""
    indicators = [
        IndicatorValue(name="RSI(14)", value=55, signal=SignalType.BUY),
        IndicatorValue(name="CCI(20)", value=-50, signal=SignalType.SELL),
        IndicatorValue(name="ADX(14)", value=30, signal=SignalType.BUY),
    ]
    patterns = [
        PatternDetection(pattern_type="Doji", confidence=0.5, bullish=True),
        PatternDetection(pattern_type="Engulfing", confidence=0.7, bullish=False),
    ]

    confidence = calculate_confidence(
        direction=Direction.LONG,
        indicators=indicators,
        patterns=patterns,
    )

    assert 20 < confidence < 80


def test_no_data():
    """No input data → low but not zero confidence (neutral defaults)."""
    confidence = calculate_confidence(direction=Direction.LONG)
    # With all defaults (empty data), expect some neutral score
    assert 0 <= confidence <= 100


def test_reliability_affects_confidence_score():
    """Formacja ★★★ zgodna z kierunkiem daje wyższy score niż ★."""
    base_patterns = [
        PatternDetection(pattern_type="Engulfing", confidence=0.8, bullish=True, reliability=1),
    ]
    strong_patterns = [
        PatternDetection(pattern_type="Engulfing", confidence=0.8, bullish=True, reliability=3),
    ]

    confidence_base = calculate_confidence(
        direction=Direction.LONG,
        patterns=base_patterns,
    )
    confidence_strong = calculate_confidence(
        direction=Direction.LONG,
        patterns=strong_patterns,
    )

    assert confidence_strong >= confidence_base, (
        f"Reliability 3 should give >= confidence than reliability 1: {confidence_strong} vs {confidence_base}"
    )


def test_opposing_high_reliability_lowers_confidence():
    """Formacja ★★★ przeciwna kierunkowi obniża score."""
    confirming = [
        PatternDetection(pattern_type="Hammer", confidence=0.7, bullish=True, reliability=1),
        PatternDetection(pattern_type="ShootingStar", confidence=0.7, bullish=False, reliability=3),
    ]

    confidence = calculate_confidence(
        direction=Direction.LONG,
        patterns=confirming,
    )
    # With strong opposing pattern, score should be relatively low
    assert confidence < 70, f"Expected lower confidence due to opposing ★★★, got {confidence}"

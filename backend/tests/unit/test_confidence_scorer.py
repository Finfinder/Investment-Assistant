"""Tests for strategy_generator/confidence_scorer.py"""

import pytest

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


def test_relevance_score_higher_than_confidence():
    """Formacja zgodna z wyższym relevance_score daje wyższy score niż formacja z niższym relevance_score."""
    low_relevance = [
        PatternDetection(pattern_type="Engulfing", confidence=0.8, bullish=True, relevance_score=0.3),
    ]
    high_relevance = [
        PatternDetection(pattern_type="Engulfing", confidence=0.8, bullish=True, relevance_score=0.8),
    ]

    confidence_low = calculate_confidence(
        direction=Direction.LONG,
        patterns=low_relevance,
    )
    confidence_high = calculate_confidence(
        direction=Direction.LONG,
        patterns=high_relevance,
    )

    assert confidence_high > confidence_low, (
        f"Higher relevance_score should give higher confidence: {confidence_high} vs {confidence_low}"
    )


def test_relevance_score_fallback_to_confidence():
    """Gdy relevance_score == 0.0, fallback do confidence zachowuje kierunek sygnału."""
    patterns = [
        PatternDetection(pattern_type="Hammer", confidence=0.9, bullish=True, relevance_score=0.0),
    ]

    confidence = calculate_confidence(
        direction=Direction.LONG,
        patterns=patterns,
    )

    assert confidence > 0, f"Fallback to confidence should produce positive confidence, got {confidence}"


def test_opposing_high_relevance_obniza_confidence():
    """Niedźwiedzia formacja z wysokim relevance_score obniża pewność silniej niż z niskim."""
    low_rel_opposing = [
        PatternDetection(pattern_type="Hammer", confidence=0.8, bullish=True, relevance_score=0.8),
        PatternDetection(pattern_type="ShootingStar", confidence=0.8, bullish=False, relevance_score=0.2),
    ]
    high_rel_opposing = [
        PatternDetection(pattern_type="Hammer", confidence=0.8, bullish=True, relevance_score=0.8),
        PatternDetection(pattern_type="ShootingStar", confidence=0.8, bullish=False, relevance_score=0.8),
    ]

    confidence_low = calculate_confidence(
        direction=Direction.LONG,
        patterns=low_rel_opposing,
    )
    confidence_high = calculate_confidence(
        direction=Direction.LONG,
        patterns=high_rel_opposing,
    )

    assert confidence_low > confidence_high, (
        f"High-relevance opposing pattern should lower confidence more: {confidence_low} vs {confidence_high}"
    )


def test_opposing_high_relevance_obniza_confidence_for_short():
    """Bycza formacja przeciwna dla SHORT z wysokim relevance_score silniej obniża pewność niż z niskim."""
    low_rel_opposing = [
        PatternDetection(pattern_type="ShootingStar", confidence=0.8, bullish=False, relevance_score=0.8),
        PatternDetection(pattern_type="Engulfing", confidence=0.8, bullish=True, relevance_score=0.2),
    ]
    high_rel_opposing = [
        PatternDetection(pattern_type="ShootingStar", confidence=0.8, bullish=False, relevance_score=0.8),
        PatternDetection(pattern_type="Engulfing", confidence=0.8, bullish=True, relevance_score=0.8),
    ]

    confidence_low = calculate_confidence(
        direction=Direction.SHORT,
        patterns=low_rel_opposing,
    )
    confidence_high = calculate_confidence(
        direction=Direction.SHORT,
        patterns=high_rel_opposing,
    )

    assert confidence_low > confidence_high, (
        "High-relevance bullish opposing pattern should lower SHORT confidence more: "
        f"{confidence_low} vs {confidence_high}"
    )


def test_reliability_amplifies_at_equal_relevance_score():
    """Przy równym relevance_score wyższe reliability przesuwa wynik ku formacji o wyższej wiarygodności."""
    bull_high_rel = [
        PatternDetection(pattern_type="Engulfing", confidence=0.8, bullish=True, reliability=3, relevance_score=0.7),
        PatternDetection(
            pattern_type="ShootingStar", confidence=0.8, bullish=False, reliability=1, relevance_score=0.7
        ),
    ]
    bull_low_rel = [
        PatternDetection(pattern_type="Engulfing", confidence=0.8, bullish=True, reliability=1, relevance_score=0.7),
        PatternDetection(
            pattern_type="ShootingStar", confidence=0.8, bullish=False, reliability=3, relevance_score=0.7
        ),
    ]

    confidence_bull_high = calculate_confidence(
        direction=Direction.LONG,
        patterns=bull_high_rel,
    )
    confidence_bear_high = calculate_confidence(
        direction=Direction.LONG,
        patterns=bull_low_rel,
    )

    assert confidence_bull_high > confidence_bear_high, (
        f"Higher reliability bullish should win with equal relevance: {confidence_bull_high} vs {confidence_bear_high}"
    )


def test_ta_agreement_short_with_indicators():
    """SHORT + bearish indicators yields higher confidence than LONG (kills _BEARISH_SIGNALS mutants)."""
    indicators = [
        IndicatorValue(name="RSI(14)", value=25, signal=SignalType.SELL),
        IndicatorValue(name="MACD(12,26,9)", value=-0.5, signal=SignalType.SELL),
    ]
    short_conf = calculate_confidence(direction=Direction.SHORT, indicators=indicators)
    long_conf = calculate_confidence(direction=Direction.LONG, indicators=indicators)
    # Bearish indicators agree with SHORT but oppose LONG
    assert short_conf > long_conf
    assert short_conf > 50


def test_ta_agreement_short_with_signal_summary():
    """SHORT + bearish signal_summary yields higher confidence than LONG (kills +/- and /total mutants)."""
    summary = SignalSummary(
        overall_summary=SignalType.STRONG_SELL,
        overall_buy_count=1,
        overall_sell_count=8,
        overall_neutral_count=1,
    )
    short_conf = calculate_confidence(direction=Direction.SHORT, signal_summary=summary)
    long_conf = calculate_confidence(direction=Direction.LONG, signal_summary=summary)
    # SHORT uses sell_count/total = 8/10 = 0.8 → higher than LONG's 1/10
    assert short_conf > long_conf
    assert short_conf > 40


def test_fundamental_alignment_long_positive():
    """LONG + positive fundamental score → (score+100)/200 (kills fundamental branch mutants)."""
    from app.modules.strategy_generator.confidence_scorer import _fundamental_alignment

    result = _fundamental_alignment(Direction.LONG, FundamentalData(instrument_type=InstrumentType.FOREX, score=70))
    assert abs(result - 0.85) < 1e-9


def test_fundamental_alignment_short_positive():
    """SHORT + positive fundamental score → (-score+100)/200 (kills fundamental branch mutants)."""
    from app.modules.strategy_generator.confidence_scorer import _fundamental_alignment

    result = _fundamental_alignment(Direction.SHORT, FundamentalData(instrument_type=InstrumentType.FOREX, score=70))
    assert abs(result - 0.15) < 1e-9


def test_adx_strength_detected():
    """ADX indicator with value → trend strength = min(1, value/50) (kills startswith/is-None mutants)."""
    from app.modules.strategy_generator.confidence_scorer import _adx_strength

    indicators = [IndicatorValue(name="ADX(14)", value=40, signal=SignalType.BUY)]
    assert abs(_adx_strength(indicators) - 0.8) < 1e-9


def test_adx_strength_none_value():
    """ADX indicator with None value → neutral 0.5 (kills is-None / and-or mutants)."""
    from app.modules.strategy_generator.confidence_scorer import _adx_strength

    indicators = [IndicatorValue(name="ADX(14)", value=None, signal=SignalType.BUY)]
    assert _adx_strength(indicators) == 0.5


def test_no_data_confidence_is_deterministic():
    """No input data → fixed, deterministic baseline confidence (regression for python:S1244 fix).

    The scorer must return a stable, known value (17.5) when given no signals,
    not a 'neutral' midpoint — the baseline reflects the scorer's default
    weighting in the absence of evidence. The weights in calculate_confidence
    are fixed (0.40/0.25/0.15/0.20), so total_weight is always 1.0
    and the epsilon guard is defensive. This test anchors the pre-change
    behaviour so any future change to the guard or the weights is caught. The
    fix replaced `total_weight == 0` with
    `abs(total_weight) < _FLOAT_ZERO_EPSILON` to clear the SonarCloud
    python:S1244 finding without altering runtime behaviour.
    """
    confidence = calculate_confidence(direction=Direction.LONG)
    assert confidence == pytest.approx(17.5)


def test_confidence_within_range_for_edge_inputs():
    """Edge inputs (all neutral) → confidence stays within [0, 100] and is stable.

    Exercises the public API with neutral signals/patterns/fundamentals to ensure
    the epsilon-guarded division never produces an out-of-range or unstable value.
    """
    indicators = [
        IndicatorValue(name="RSI(14)", value=50, signal=SignalType.NEUTRAL),
    ]
    patterns = [
        PatternDetection(pattern_type="Doji", confidence=0.0, bullish=True, relevance_score=0.0),
    ]
    fundamental = FundamentalData(instrument_type=InstrumentType.FOREX, score=0)

    confidence = calculate_confidence(
        direction=Direction.LONG,
        indicators=indicators,
        signal_summary=SignalSummary(
            overall_summary=SignalType.NEUTRAL,
            overall_buy_count=0,
            overall_sell_count=0,
            overall_neutral_count=1,
        ),
        patterns=patterns,
        fundamental=fundamental,
    )

    assert 0.0 <= confidence <= 100.0

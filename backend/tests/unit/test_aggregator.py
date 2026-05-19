"""Tests for signal_aggregation/aggregator.py"""

import pytest

from app.core.models import (
    FundamentalData,
    IndicatorValue,
    InstrumentType,
    MovingAverage,
    PatternDetection,
    SignalType,
)
from app.modules.signal_aggregation.aggregator import SignalAggregator


def test_all_bullish_signals():
    """All signals point bullish → positive normalized values."""
    indicators = [
        IndicatorValue(name="RSI", value=70, signal=SignalType.BUY),
        IndicatorValue(name="MACD", value=0.5, signal=SignalType.STRONG_BUY),
    ]
    mas = [MovingAverage(period=50, sma_signal=SignalType.BUY, ema_signal=SignalType.BUY)]
    patterns = [
        PatternDetection(pattern_type="Hammer", confidence=0.8, bullish=True),
        PatternDetection(pattern_type="Engulfing", confidence=0.9, bullish=True),
    ]
    fundamental = FundamentalData(instrument_type=InstrumentType.FOREX, score=60)

    agg = SignalAggregator(
        indicators=indicators,
        moving_averages=mas,
        patterns=patterns,
        fundamental=fundamental,
    )

    assert agg.normalize_ta_signal() > 0
    assert agg.normalize_pattern_signal() > 0
    assert agg.normalize_fundamental_signal() > 0

    signals = agg.get_all_signals()
    assert signals["technical_analysis"] > 0
    assert signals["patterns"] > 0
    assert signals["fundamental"] > 0


def test_all_bearish_signals():
    """All signals point bearish → negative normalized values."""
    indicators = [
        IndicatorValue(name="RSI", value=25, signal=SignalType.SELL),
        IndicatorValue(name="MACD", value=-0.5, signal=SignalType.STRONG_SELL),
    ]
    mas = [MovingAverage(period=200, sma_signal=SignalType.SELL, ema_signal=SignalType.SELL)]
    patterns = [
        PatternDetection(pattern_type="ShootingStar", confidence=0.7, bullish=False),
    ]
    fundamental = FundamentalData(instrument_type=InstrumentType.INDEX, score=-50)

    agg = SignalAggregator(
        indicators=indicators,
        moving_averages=mas,
        patterns=patterns,
        fundamental=fundamental,
    )

    assert agg.normalize_ta_signal() < 0
    assert agg.normalize_pattern_signal() < 0
    assert agg.normalize_fundamental_signal() < 0


def test_mixed_signals():
    """Mixed signals → scores near zero."""
    indicators = [
        IndicatorValue(name="RSI", value=50, signal=SignalType.NEUTRAL),
        IndicatorValue(name="CCI", value=10, signal=SignalType.BUY),
    ]
    mas = [MovingAverage(period=50, sma_signal=SignalType.SELL, ema_signal=SignalType.BUY)]
    patterns = [
        PatternDetection(pattern_type="Doji", confidence=0.5, bullish=True),
        PatternDetection(pattern_type="Engulfing", confidence=0.5, bullish=False),
    ]

    agg = SignalAggregator(indicators=indicators, moving_averages=mas, patterns=patterns)

    ta = agg.normalize_ta_signal()
    pattern = agg.normalize_pattern_signal()
    # Both should be close to 0
    assert -0.5 < ta < 0.5
    assert -0.5 < pattern < 0.5


def test_empty_inputs():
    """No data → all signals return 0."""
    agg = SignalAggregator()
    signals = agg.get_all_signals()
    assert signals["technical_analysis"] == 0.0
    assert signals["patterns"] == 0.0
    assert signals["fundamental"] == 0.0


def test_reliability_multiplier_increases_weight():
    """Formacja z reliability=3 ma większy wpływ niż reliability=1."""
    # Dwie bycze formacje: jedna ★★★, jedna niedźwiedzia ★
    # Gdyby oba miały reliability=1, wynik = 0 (offset)
    # Ale bycza ma wagę 1.0*1.6=1.6, niedźwiedzia 1.0*1.0=1.0 → wynik > 0
    patterns_high_reliability = [
        PatternDetection(pattern_type="Engulfing", confidence=1.0, bullish=True, reliability=3),
        PatternDetection(pattern_type="ShootingStar", confidence=1.0, bullish=False, reliability=1),
    ]
    agg_high = SignalAggregator(patterns=patterns_high_reliability)
    signal_high = agg_high.normalize_pattern_signal()
    assert signal_high > 0, f"Expected positive signal, got {signal_high}"

    # Symetrycznie: niedźwiedzia ★★★, bycza ★ → wynik < 0
    patterns_low_reliability = [
        PatternDetection(pattern_type="Engulfing", confidence=1.0, bullish=True, reliability=1),
        PatternDetection(pattern_type="ShootingStar", confidence=1.0, bullish=False, reliability=3),
    ]
    agg_low = SignalAggregator(patterns=patterns_low_reliability)
    signal_low = agg_low.normalize_pattern_signal()
    assert signal_low < 0, f"Expected negative signal, got {signal_low}"

    # Wynik z ★★★ ma większy efekt niż bez mnożnika
    assert abs(signal_high) > 0, "High reliability should produce non-zero signal"


def test_all_same_direction_reliability_does_not_change_sign():
    """Reliability nie zmienia znaku wyniku — tylko wzmacnia."""
    patterns = [
        PatternDetection(pattern_type="Hammer", confidence=0.7, bullish=True, reliability=1),
        PatternDetection(pattern_type="Engulfing", confidence=0.8, bullish=True, reliability=3),
    ]
    agg = SignalAggregator(patterns=patterns)
    signal = agg.normalize_pattern_signal()
    assert signal > 0, "All bullish patterns → positive signal regardless of reliability"


def test_higher_relevance_score_bullish_dominates_lower_bearish():
    """Bycza formacja z wyższym relevance_score dominuje nad niedźwiedzią z niższym."""
    patterns = [
        PatternDetection(pattern_type="Engulfing", confidence=0.8, bullish=True, reliability=1, relevance_score=0.9),
        PatternDetection(
            pattern_type="ShootingStar", confidence=0.8, bullish=False, reliability=1, relevance_score=0.2
        ),
    ]
    agg = SignalAggregator(patterns=patterns)
    signal = agg.normalize_pattern_signal()
    assert signal > 0, f"High-relevance bullish should dominate, got {signal}"


def test_higher_relevance_score_bearish_dominates_lower_bullish():
    """Niedźwiedzia formacja z wyższym relevance_score dominuje nad byczą z niższym."""
    patterns = [
        PatternDetection(pattern_type="Engulfing", confidence=0.8, bullish=True, reliability=1, relevance_score=0.2),
        PatternDetection(
            pattern_type="ShootingStar", confidence=0.8, bullish=False, reliability=1, relevance_score=0.9
        ),
    ]
    agg = SignalAggregator(patterns=patterns)
    signal = agg.normalize_pattern_signal()
    assert signal < 0, f"High-relevance bearish should dominate, got {signal}"


def test_fallback_to_confidence_when_relevance_score_is_zero():
    """Gdy relevance_score == 0.0, fallback do confidence zachowuje kierunek sygnału."""
    patterns = [
        PatternDetection(pattern_type="Hammer", confidence=0.9, bullish=True, relevance_score=0.0),
    ]
    agg = SignalAggregator(patterns=patterns)
    signal = agg.normalize_pattern_signal()
    assert signal > 0, f"Fallback to confidence should produce positive signal, got {signal}"


def test_fallback_bearish_confidence_when_relevance_score_is_zero():
    """Gdy relevance_score == 0.0, fallback do confidence zachowuje ujemny kierunek."""
    patterns = [
        PatternDetection(pattern_type="ShootingStar", confidence=0.8, bullish=False, relevance_score=0.0),
    ]
    agg = SignalAggregator(patterns=patterns)
    signal = agg.normalize_pattern_signal()
    assert signal < 0, f"Fallback to confidence should produce negative signal, got {signal}"


def test_reliability_amplifies_relevance_score():
    """Przy równym relevance_score wyższe reliability przesuwa wynik ku formacji o wyższej wiarygodności."""
    # Bycza ★★★ vs niedźwiedzia ★, oba z równym relevance_score → wynik > 0
    patterns_bull_high_rel = [
        PatternDetection(pattern_type="Engulfing", confidence=0.8, bullish=True, reliability=3, relevance_score=0.7),
        PatternDetection(
            pattern_type="ShootingStar", confidence=0.8, bullish=False, reliability=1, relevance_score=0.7
        ),
    ]
    agg = SignalAggregator(patterns=patterns_bull_high_rel)
    assert agg.normalize_pattern_signal() > 0, "Higher reliability bullish should win with equal relevance"

    # Symetrycznie: niedźwiedzia ★★★ vs bycza ★ → wynik < 0
    patterns_bear_high_rel = [
        PatternDetection(pattern_type="Engulfing", confidence=0.8, bullish=True, reliability=1, relevance_score=0.7),
        PatternDetection(
            pattern_type="ShootingStar", confidence=0.8, bullish=False, reliability=3, relevance_score=0.7
        ),
    ]
    agg2 = SignalAggregator(patterns=patterns_bear_high_rel)
    assert agg2.normalize_pattern_signal() < 0, "Higher reliability bearish should win with equal relevance"


def test_low_relevance_score_does_not_saturate_signal():
    """Pojedyncza formacja z niskim relevance_score nie produkuje saturowanego ±1.0."""
    patterns_low = [
        PatternDetection(pattern_type="Hammer", confidence=0.9, bullish=True, relevance_score=0.2),
    ]
    agg_low = SignalAggregator(patterns=patterns_low)
    signal_low = agg_low.normalize_pattern_signal()
    assert signal_low == pytest.approx(0.2), f"Low relevance_score=0.2 should give ~0.2, got {signal_low}"

    patterns_high = [
        PatternDetection(pattern_type="Hammer", confidence=0.9, bullish=True, relevance_score=0.8),
    ]
    agg_high = SignalAggregator(patterns=patterns_high)
    signal_high = agg_high.normalize_pattern_signal()
    assert signal_high == pytest.approx(0.8), f"High relevance_score=0.8 should give ~0.8, got {signal_high}"

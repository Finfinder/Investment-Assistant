"""Tests for signal_aggregation/aggregator.py"""

from app.core.models import (
    FundamentalData,
    IndicatorValue,
    InstrumentType,
    MovingAverage,
    PatternDetection,
    SignalSummary,
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


def test_signal_summary_overrides_individual():
    """When signal_summary is provided, it overrides individual indicators."""
    indicators = [IndicatorValue(name="RSI", value=70, signal=SignalType.BUY)]
    summary = SignalSummary(overall_summary=SignalType.STRONG_SELL)

    agg = SignalAggregator(indicators=indicators, signal_summary=summary)
    # Summary should take precedence
    assert agg.normalize_ta_signal() == -1.0

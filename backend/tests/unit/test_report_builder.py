"""Tests for strategy_generator/report_builder.py"""

from datetime import UTC, datetime

from app.core.models import (
    Direction,
    FundamentalData,
    IndicatorValue,
    InstrumentType,
    MovingAverage,
    OHLCVData,
    PatternDetection,
    SignalSummary,
    SignalType,
    Timeframe,
)
from app.modules.strategy_generator.report_builder import build_report


def _make_ohlcv(n: int = 20, base_price: float = 100.0) -> list[OHLCVData]:
    data = []
    price = base_price
    for i in range(n):
        data.append(
            OHLCVData(
                timestamp=datetime(2024, 1, 1, hour=i % 24, tzinfo=UTC),
                open=price,
                high=price + 2.0,
                low=price - 1.0,
                close=price + 1.0,
                volume=1000.0,
            )
        )
        price += 1.0
    return data


def test_bullish_report():
    """Strong bullish inputs → report with LONG strategies."""
    ohlcv = _make_ohlcv(20)
    indicators = [
        IndicatorValue(name="RSI(14)", value=65, signal=SignalType.BUY),
        IndicatorValue(name="ADX(14)", value=35, signal=SignalType.BUY),
    ]
    mas = [MovingAverage(period=50, sma_signal=SignalType.BUY, ema_signal=SignalType.BUY)]
    summary = SignalSummary(
        overall_summary=SignalType.BUY,
        overall_buy_count=8,
        overall_sell_count=1,
        overall_neutral_count=1,
    )
    patterns = [
        PatternDetection(
            pattern_type="S/R Level (support)",
            confidence=0.7,
            description="Support at 110.00 (3 touches)",
            bullish=True,
        ),
    ]
    fundamental = FundamentalData(instrument_type=InstrumentType.FOREX, score=50)

    report = build_report(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        ohlcv=ohlcv,
        indicators=indicators,
        moving_averages=mas,
        pivot_points=[],
        patterns=patterns,
        signal_summary=summary,
        fundamental=fundamental,
    )

    assert report.symbol == "EURUSD"
    assert report.timeframe == Timeframe.H1
    assert len(report.strategies) >= 1
    assert all(s.direction == Direction.LONG for s in report.strategies)
    assert all(s.entry_price is not None for s in report.strategies)
    assert all(s.stop_loss is not None for s in report.strategies)


def test_bearish_report():
    """Strong bearish inputs → report with SHORT strategies."""
    ohlcv = _make_ohlcv(20)
    indicators = [
        IndicatorValue(name="RSI(14)", value=25, signal=SignalType.SELL),
        IndicatorValue(name="ADX(14)", value=40, signal=SignalType.SELL),
    ]
    mas = [MovingAverage(period=50, sma_signal=SignalType.SELL, ema_signal=SignalType.SELL)]
    summary = SignalSummary(
        overall_summary=SignalType.STRONG_SELL,
        overall_buy_count=0,
        overall_sell_count=9,
        overall_neutral_count=1,
    )
    patterns = [
        PatternDetection(
            pattern_type="S/R Level (resistance)",
            confidence=0.8,
            description="Resistance at 125.00 (4 touches)",
            bullish=False,
        ),
    ]
    fundamental = FundamentalData(instrument_type=InstrumentType.FOREX, score=-60)

    report = build_report(
        symbol="GBPUSD",
        timeframe=Timeframe.D1,
        ohlcv=ohlcv,
        indicators=indicators,
        moving_averages=mas,
        pivot_points=[],
        patterns=patterns,
        signal_summary=summary,
        fundamental=fundamental,
    )

    assert len(report.strategies) >= 1
    assert all(s.direction == Direction.SHORT for s in report.strategies)


def test_neutral_report_no_strategies():
    """Neutral inputs → report with no strategies."""
    ohlcv = _make_ohlcv(20)
    indicators = [IndicatorValue(name="RSI(14)", value=50, signal=SignalType.NEUTRAL)]
    summary = SignalSummary(overall_summary=SignalType.NEUTRAL)

    report = build_report(
        symbol="USDJPY",
        timeframe=Timeframe.H4,
        ohlcv=ohlcv,
        indicators=indicators,
        moving_averages=[],
        pivot_points=[],
        patterns=[],
        signal_summary=summary,
    )

    assert report.strategies == []

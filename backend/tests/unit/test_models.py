"""Tests for domain models validation."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.core.models import (
    AnalysisReport,
    AnalysisStatus,
    AnalysisStatusType,
    Direction,
    FundamentalData,
    IndicatorValue,
    InstrumentType,
    MovingAverage,
    OHLCVData,
    PatternDetection,
    PivotPoints,
    PivotType,
    SignalSummary,
    SignalType,
    StrategyEntry,
    Timeframe,
)


class TestOHLCVData:
    def test_valid_ohlcv(self) -> None:
        data = OHLCVData(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=1000.0,
        )
        assert data.close == 103.0
        assert data.volume == 1000.0

    def test_ohlcv_default_volume(self) -> None:
        data = OHLCVData(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
        )
        assert data.volume == 0.0

    def test_ohlcv_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            OHLCVData(  # type: ignore[call-arg]
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                open=100.0,
                high=105.0,
            )


class TestIndicatorValue:
    def test_valid_indicator(self) -> None:
        iv = IndicatorValue(name="RSI", value=65.0, signal=SignalType.NEUTRAL)
        assert iv.name == "RSI"
        assert iv.value == 65.0

    def test_indicator_default_signal(self) -> None:
        iv = IndicatorValue(name="MACD", value=0.5)
        assert iv.signal == SignalType.NEUTRAL

    def test_indicator_none_value(self) -> None:
        iv = IndicatorValue(name="CCI")
        assert iv.value is None


class TestMovingAverage:
    def test_valid_ma(self) -> None:
        ma = MovingAverage(
            period=50,
            sma_value=105.5,
            sma_signal=SignalType.BUY,
            ema_value=106.0,
            ema_signal=SignalType.BUY,
        )
        assert ma.period == 50
        assert ma.sma_signal == SignalType.BUY


class TestPivotPoints:
    def test_valid_pivot(self) -> None:
        pp = PivotPoints(
            type=PivotType.CLASSIC,
            pp=100.0,
            s1=98.0,
            s2=96.0,
            s3=94.0,
            r1=102.0,
            r2=104.0,
            r3=106.0,
        )
        assert pp.type == PivotType.CLASSIC
        assert pp.pp == 100.0


class TestPatternDetection:
    def test_valid_pattern(self) -> None:
        p = PatternDetection(
            pattern_type="engulfing",
            confidence=0.85,
            description="Bullish engulfing",
            bullish=True,
        )
        assert p.confidence == 0.85

    def test_confidence_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            PatternDetection(pattern_type="test", confidence=1.5)

    def test_confidence_negative(self) -> None:
        with pytest.raises(ValidationError):
            PatternDetection(pattern_type="test", confidence=-0.1)


class TestFundamentalData:
    def test_valid_fundamental(self) -> None:
        fd = FundamentalData(
            instrument_type=InstrumentType.FOREX,
            indicators={"interest_rate_diff": 1.5},
            score=45.0,
            summary="USD stronger",
        )
        assert fd.score == 45.0

    def test_score_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            FundamentalData(
                instrument_type=InstrumentType.FOREX,
                score=150.0,
            )


class TestSignalSummary:
    def test_defaults(self) -> None:
        ss = SignalSummary()
        assert ss.ma_summary == SignalType.NEUTRAL
        assert ss.overall_buy_count == 0


class TestStrategyEntry:
    def test_valid_strategy(self) -> None:
        se = StrategyEntry(
            direction=Direction.LONG,
            entry_condition="Buy at market",
            entry_price=105.0,
            stop_loss=100.0,
            tp1=110.0,
            tp2=115.0,
            confidence_pct=75.0,
        )
        assert se.direction == Direction.LONG
        assert se.confidence_pct == 75.0

    def test_confidence_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            StrategyEntry(direction=Direction.LONG, confidence_pct=150.0)


class TestAnalysisReport:
    def test_minimal_report(self) -> None:
        report = AnalysisReport(symbol="EURUSD", timeframe=Timeframe.H1)
        assert report.symbol == "EURUSD"
        assert report.technical_indicators == []
        assert report.strategies == []

    def test_full_report(self) -> None:
        report = AnalysisReport(
            symbol="GOLD",
            timeframe=Timeframe.D1,
            technical_indicators=[IndicatorValue(name="RSI", value=30.0, signal=SignalType.BUY)],
            signal_summary=SignalSummary(overall_summary=SignalType.BUY),
            strategies=[StrategyEntry(direction=Direction.LONG, confidence_pct=80.0)],
        )
        assert len(report.technical_indicators) == 1
        assert report.signal_summary is not None
        assert report.signal_summary.overall_summary == SignalType.BUY

    def test_instrument_type_default_none(self) -> None:
        report = AnalysisReport(symbol="EURUSD", timeframe=Timeframe.H1)
        assert report.instrument_type is None

    def test_instrument_type_explicit(self) -> None:
        report = AnalysisReport(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            instrument_type=InstrumentType.FOREX,
        )
        assert report.instrument_type == InstrumentType.FOREX


class TestAnalysisStatus:
    def test_valid_status(self) -> None:
        status = AnalysisStatus(
            id="abc-123",
            status=AnalysisStatusType.RUNNING,
            progress_pct=50.0,
            current_step="Technical Analysis",
            steps_completed=["Data Fetch"],
        )
        assert status.progress_pct == 50.0
        assert len(status.steps_completed) == 1

    def test_progress_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            AnalysisStatus(id="test", progress_pct=150.0)

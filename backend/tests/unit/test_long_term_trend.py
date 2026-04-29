from datetime import UTC, datetime
from unittest.mock import patch

from app.core.models import IndicatorPreset, MovingAverage, OHLCVData, SignalSummary, SignalType
from app.modules.technical_analysis.long_term_trend import build_long_term_trend


def _make_ohlcv(n: int = 20) -> list[OHLCVData]:
    return [
        OHLCVData(
            timestamp=datetime(2024, 1, 1, hour=index % 24, tzinfo=UTC),
            open=100.0 + index,
            high=101.0 + index,
            low=99.0 + index,
            close=100.5 + index,
            volume=1000.0 + index,
        )
        for index in range(n)
    ]


def test_build_long_term_trend_returns_weekly_summary() -> None:
    with (
        patch(
            "app.modules.technical_analysis.long_term_trend.calculate_indicators",
            return_value=[],
        ),
        patch(
            "app.modules.technical_analysis.long_term_trend.calculate_moving_averages",
            return_value=[MovingAverage(period=50, sma_signal=SignalType.BUY)],
        ),
        patch(
            "app.modules.technical_analysis.long_term_trend.calculate_summaries",
            return_value=SignalSummary(overall_summary=SignalType.STRONG_BUY),
        ),
    ):
        result = build_long_term_trend(_make_ohlcv(), IndicatorPreset.INVESTING)

    assert result is not None
    assert result.signal == SignalType.STRONG_BUY
    assert result.summary == "Silny trend wzrostowy"
    assert result.source_label == "weekly"


def test_build_long_term_trend_returns_none_when_analysis_data_missing() -> None:
    with (
        patch(
            "app.modules.technical_analysis.long_term_trend.calculate_indicators",
            side_effect=RuntimeError("indicators failed"),
        ),
        patch(
            "app.modules.technical_analysis.long_term_trend.calculate_moving_averages",
            side_effect=RuntimeError("ma failed"),
        ),
    ):
        result = build_long_term_trend(_make_ohlcv(), IndicatorPreset.INVESTING)

    assert result is None

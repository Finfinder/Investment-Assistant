from app.core.models import Timeframe
from app.modules.data_acquisition.timeframes import DataTimeframe, resolve_analysis_timeframes
from app.orchestration.pipeline import AnalysisPipeline


def test_public_timeframe_enum_does_not_expose_weekly() -> None:
    assert "W1" not in {timeframe.value for timeframe in Timeframe}


def test_resolver_returns_deterministic_pattern_scanner_timeframes() -> None:
    plan = resolve_analysis_timeframes(Timeframe.H4)

    assert plan.main_timeframe == DataTimeframe.H4
    assert plan.pivot_points_timeframe == DataTimeframe.D1
    assert plan.long_term_trend_timeframe == DataTimeframe.W1
    assert plan.pattern_scanner_timeframes == (
        DataTimeframe.D1,
        DataTimeframe.H1,
        DataTimeframe.M15,
    )
    assert plan.required_timeframes == (
        DataTimeframe.H4,
        DataTimeframe.D1,
        DataTimeframe.W1,
        DataTimeframe.H1,
        DataTimeframe.M15,
    )


def test_resolver_deduplicates_daily_main_timeframe() -> None:
    plan = resolve_analysis_timeframes(Timeframe.D1)

    assert plan.required_timeframes == (
        DataTimeframe.D1,
        DataTimeframe.W1,
        DataTimeframe.H1,
        DataTimeframe.M15,
    )


def test_internal_weekly_timeframe_cannot_be_mapped_to_public_enum() -> None:
    assert DataTimeframe.W1.to_public() is None


def test_pipeline_prepares_internal_timeframe_plan() -> None:
    pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1)

    assert pipeline.timeframe_plan.main_timeframe == DataTimeframe.H1
    assert pipeline.timeframe_plan.required_timeframes == (
        DataTimeframe.H1,
        DataTimeframe.D1,
        DataTimeframe.W1,
        DataTimeframe.M15,
    )

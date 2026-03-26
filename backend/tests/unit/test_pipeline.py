"""Tests for modules/pipeline.py"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.models import AnalysisStatusType, OHLCVData, Timeframe
from app.modules.pipeline import AnalysisPipeline, analysis_tasks


def _make_ohlcv(n: int = 20) -> list[OHLCVData]:
    data = []
    price = 100.0
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


@pytest.fixture(autouse=True)
def _clean_tasks():
    """Clear shared analysis_tasks between tests."""
    analysis_tasks.clear()
    yield
    analysis_tasks.clear()


@pytest.mark.asyncio
async def test_pipeline_success():
    """Full pipeline with mocked providers produces a completed report."""
    mock_chain = MagicMock()
    mock_chain.fetch_ohlcv = AsyncMock(return_value=_make_ohlcv(30))

    pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=mock_chain)

    with (
        patch(
            "app.modules.pipeline.AnalysisPipeline._step_fundamental_analysis",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.modules.pipeline.AnalysisPipeline._persist_result",
            new_callable=AsyncMock,
        ),
    ):
        report = await pipeline.run()

    assert report is not None
    assert report.symbol == "EURUSD"
    assert report.timeframe == Timeframe.H1
    assert pipeline.status.status == AnalysisStatusType.COMPLETED
    assert pipeline.status.progress_pct == 100.0
    assert len(pipeline.status.steps_completed) == 6


@pytest.mark.asyncio
async def test_pipeline_partial_failure():
    """Pipeline succeeds even when fundamental analysis fails."""
    mock_chain = MagicMock()
    mock_chain.fetch_ohlcv = AsyncMock(return_value=_make_ohlcv(30))

    pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=mock_chain)

    with (
        patch(
            "app.modules.pipeline.AnalysisPipeline._step_fundamental_analysis",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.modules.pipeline.AnalysisPipeline._persist_result",
            new_callable=AsyncMock,
        ),
    ):
        report = await pipeline.run()

    assert report is not None
    assert report.fundamental is None
    assert pipeline.status.status == AnalysisStatusType.COMPLETED


@pytest.mark.asyncio
async def test_pipeline_data_fetch_failure():
    """Pipeline fails when market data cannot be fetched."""
    mock_chain = MagicMock()
    mock_chain.fetch_ohlcv = AsyncMock(return_value=[])

    pipeline = AnalysisPipeline(symbol="INVALID", timeframe=Timeframe.H1, chain=mock_chain)

    report = await pipeline.run()

    assert report is None
    assert pipeline.status.status == AnalysisStatusType.FAILED
    assert pipeline.status.error_message is not None


@pytest.mark.asyncio
async def test_pipeline_status_tracking():
    """Pipeline correctly updates status in the shared dict."""
    mock_chain = MagicMock()
    mock_chain.fetch_ohlcv = AsyncMock(return_value=_make_ohlcv(30))

    pipeline = AnalysisPipeline(symbol="GBPUSD", timeframe=Timeframe.H4, chain=mock_chain)

    assert pipeline.analysis_id in analysis_tasks
    assert analysis_tasks[pipeline.analysis_id].status == AnalysisStatusType.PENDING

    with (
        patch(
            "app.modules.pipeline.AnalysisPipeline._step_fundamental_analysis",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.modules.pipeline.AnalysisPipeline._persist_result",
            new_callable=AsyncMock,
        ),
    ):
        await pipeline.run()

    status = analysis_tasks[pipeline.analysis_id]
    assert status.status == AnalysisStatusType.COMPLETED
    assert status.progress_pct == 100.0

"""Integration tests for the full analysis pipeline — trigger → poll → report."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.models import (
    AnalysisStatusType,
    FundamentalData,
    InstrumentType,
    OHLCVData,
    Timeframe,
)
from app.modules.pipeline import AnalysisPipeline, analysis_tasks


def _make_ohlcv(n: int = 50, base_price: float = 100.0) -> list[OHLCVData]:
    """Generate realistic OHLCV data for testing."""
    data: list[OHLCVData] = []
    price = base_price
    for i in range(n):
        data.append(
            OHLCVData(
                timestamp=datetime(2024, 1, 1 + i // 24, hour=i % 24, tzinfo=UTC),
                open=price,
                high=price + 2.0,
                low=price - 1.0,
                close=price + 1.0,
                volume=1000.0 + i * 100,
            )
        )
        price += 0.5
    return data


@pytest.fixture(autouse=True)
def _clean_tasks():
    analysis_tasks.clear()
    yield
    analysis_tasks.clear()


@pytest.mark.integration
class TestFullPipelineForex:
    """Full pipeline test for Forex instrument (EURUSD)."""

    @pytest.mark.asyncio
    async def test_forex_pipeline_complete_report(self) -> None:
        mock_chain = MagicMock()
        mock_chain.fetch_ohlcv = AsyncMock(return_value=_make_ohlcv(50, base_price=1.08))

        pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=mock_chain)

        with (
            patch(
                "app.modules.pipeline.AnalysisPipeline._step_fundamental_analysis",
                new_callable=AsyncMock,
                return_value=FundamentalData(
                    instrument_type="forex",
                    score=25.0,
                    indicators={},
                ),
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
        assert report.instrument_type == InstrumentType.FOREX

        # Verify report contains all required sections
        assert len(report.technical_indicators) > 0, "Report must have technical indicators"
        assert len(report.moving_averages) > 0, "Report must have moving averages"
        assert len(report.pivot_points) > 0, "Report must have pivot points"
        assert len(report.strategies) > 0, "Report must have strategies"
        assert report.signal_summary is not None, "Report must have signal summary"
        assert report.fundamental is not None, "Report must have fundamental data"

        # run() no longer publishes COMPLETED; caller must call complete()
        pipeline.complete()
        assert pipeline.status.status == AnalysisStatusType.COMPLETED
        assert pipeline.status.progress_pct == 100.0
        assert len(pipeline.status.steps_completed) == 6


@pytest.mark.integration
class TestFullPipelineCommodity:
    """Full pipeline test for Commodity instrument (GOLD)."""

    @pytest.mark.asyncio
    async def test_commodity_pipeline_complete_report(self) -> None:
        mock_chain = MagicMock()
        mock_chain.fetch_ohlcv = AsyncMock(return_value=_make_ohlcv(50, base_price=2000.0))

        pipeline = AnalysisPipeline(symbol="GOLD", timeframe=Timeframe.D1, chain=mock_chain)

        with (
            patch(
                "app.modules.pipeline.AnalysisPipeline._step_fundamental_analysis",
                new_callable=AsyncMock,
                return_value=FundamentalData(
                    instrument_type="commodity",
                    score=-10.0,
                    indicators={},
                ),
            ),
            patch(
                "app.modules.pipeline.AnalysisPipeline._persist_result",
                new_callable=AsyncMock,
            ),
        ):
            report = await pipeline.run()

        assert report is not None
        assert report.symbol == "GOLD"
        assert report.timeframe == Timeframe.D1
        assert len(report.technical_indicators) > 0
        assert len(report.moving_averages) > 0
        assert len(report.strategies) > 0
        assert report.fundamental is not None
        assert report.fundamental.instrument_type == "commodity"
        assert report.instrument_type == InstrumentType.COMMODITY


@pytest.mark.integration
class TestFullPipelineIndex:
    """Full pipeline test for Index instrument (US500)."""

    @pytest.mark.asyncio
    async def test_index_pipeline_complete_report(self) -> None:
        mock_chain = MagicMock()
        mock_chain.fetch_ohlcv = AsyncMock(return_value=_make_ohlcv(50, base_price=5200.0))

        pipeline = AnalysisPipeline(symbol="US500", timeframe=Timeframe.H4, chain=mock_chain)

        with (
            patch(
                "app.modules.pipeline.AnalysisPipeline._step_fundamental_analysis",
                new_callable=AsyncMock,
                return_value=FundamentalData(
                    instrument_type="index",
                    score=40.0,
                    indicators={},
                ),
            ),
            patch(
                "app.modules.pipeline.AnalysisPipeline._persist_result",
                new_callable=AsyncMock,
            ),
        ):
            report = await pipeline.run()

        assert report is not None
        assert report.symbol == "US500"
        assert len(report.technical_indicators) > 0
        assert len(report.strategies) > 0
        assert report.fundamental is not None
        assert report.fundamental.instrument_type == "index"
        assert report.instrument_type == InstrumentType.INDEX


@pytest.mark.integration
class TestPipelineGracefulDegradation:
    """Pipeline handles partial failures without crashing."""

    @pytest.mark.asyncio
    async def test_pipeline_without_fundamental(self) -> None:
        """Pipeline produces a valid report even when fundamental analysis fails."""
        mock_chain = MagicMock()
        mock_chain.fetch_ohlcv = AsyncMock(return_value=_make_ohlcv(50))

        pipeline = AnalysisPipeline(symbol="GBPUSD", timeframe=Timeframe.H1, chain=mock_chain)

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
        assert report.instrument_type is not None
        assert len(report.technical_indicators) > 0
        # run() no longer publishes COMPLETED; caller must call complete()
        pipeline.complete()
        assert pipeline.status.status == AnalysisStatusType.COMPLETED

    @pytest.mark.asyncio
    async def test_pipeline_no_data_fails_gracefully(self) -> None:
        """Pipeline fails with clear error when no market data is available."""
        mock_chain = MagicMock()
        mock_chain.fetch_ohlcv = AsyncMock(return_value=[])

        pipeline = AnalysisPipeline(symbol="INVALID", timeframe=Timeframe.H1, chain=mock_chain)
        report = await pipeline.run()

        assert report is None
        assert pipeline.status.status == AnalysisStatusType.FAILED
        assert pipeline.status.error_message is not None


@pytest.mark.integration
class TestApiPipelineFlow:
    """Integration test through the HTTP API layer."""

    @pytest.mark.asyncio
    async def test_trigger_and_poll_status(self, client) -> None:
        """POST /analysis → GET /analysis/{id}/status flow."""
        with patch(
            "app.api.v1.analysis._run_pipeline",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                "/api/v1/analysis",
                json={"symbol": "EURUSD", "timeframe": "H1"},
            )

        assert resp.status_code == 200
        analysis_id = resp.json()["analysis_id"]

        # Check status endpoint works
        status_resp = await client.get(f"/api/v1/analysis/{analysis_id}/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["id"] == analysis_id

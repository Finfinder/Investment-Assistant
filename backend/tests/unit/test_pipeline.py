"""Tests for modules/pipeline.py"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest import approx

from app.core.models import AnalysisStatusType, InstrumentType, OHLCVData, Timeframe
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
    # run() no longer publishes COMPLETED — caller must call complete()
    assert pipeline.status.status != AnalysisStatusType.COMPLETED
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
    # run() no longer publishes COMPLETED — caller must call complete()
    assert pipeline.status.status != AnalysisStatusType.COMPLETED


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
    # run() no longer sets COMPLETED; the status should be RUNNING (last step update)
    assert status.status == AnalysisStatusType.RUNNING

    # After calling complete(), status should be COMPLETED
    pipeline.complete()
    status = analysis_tasks[pipeline.analysis_id]
    assert status.status == AnalysisStatusType.COMPLETED
    assert status.progress_pct == approx(100.0)


def test_complete_sets_completed_status():
    """complete() sets COMPLETED status, 100% progress, and empty current_step."""
    mock_chain = MagicMock()
    pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=mock_chain)

    # Simulate running state
    pipeline._status.status = AnalysisStatusType.RUNNING
    pipeline._status.progress_pct = 83.0
    pipeline._status.current_step = "Generowanie strategii"

    pipeline.complete()

    assert pipeline.status.status == AnalysisStatusType.COMPLETED
    assert pipeline.status.progress_pct == approx(100.0)
    assert pipeline.status.current_step == ""


def test_complete_publishes_to_analysis_tasks():
    """complete() publishes the COMPLETED status to the shared analysis_tasks dict."""
    mock_chain = MagicMock()
    pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=mock_chain)

    pipeline.complete()

    published = analysis_tasks.get(pipeline.analysis_id)
    assert published is not None
    assert published.status == AnalysisStatusType.COMPLETED
    assert published.progress_pct == approx(100.0)
    assert published.current_step == ""


# ---------------------------------------------------------------------------
# _step_technical_analysis — exception isolation per sub-step
# ---------------------------------------------------------------------------
class TestStepTechnicalAnalysis:
    def _make_pipeline(self) -> AnalysisPipeline:
        chain = MagicMock()
        return AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=chain)

    def test_indicators_failure_returns_empty(self):
        pipeline = self._make_pipeline()
        ohlcv = _make_ohlcv(30)
        with patch(
            "app.modules.technical_analysis.indicators.calculate_indicators",
            side_effect=RuntimeError("boom"),
        ):
            indicators, ma, _, _ = pipeline._step_technical_analysis(ohlcv)
        assert indicators == []
        assert len(ma) > 0  # other sub-steps still succeed

    def test_moving_averages_failure_returns_empty(self):
        pipeline = self._make_pipeline()
        ohlcv = _make_ohlcv(30)
        with patch(
            "app.modules.technical_analysis.moving_averages.calculate_moving_averages",
            side_effect=RuntimeError("boom"),
        ):
            indicators, ma, _, _ = pipeline._step_technical_analysis(ohlcv)
        assert ma == []
        assert len(indicators) > 0

    def test_pivot_points_failure_returns_empty(self):
        pipeline = self._make_pipeline()
        ohlcv = _make_ohlcv(30)
        with patch(
            "app.modules.technical_analysis.pivot_points.calculate_pivot_points",
            side_effect=RuntimeError("boom"),
        ):
            _, _, pp, _ = pipeline._step_technical_analysis(ohlcv)
        assert pp == []

    def test_summary_failure_returns_none(self):
        pipeline = self._make_pipeline()
        ohlcv = _make_ohlcv(30)
        with patch(
            "app.modules.technical_analysis.summary.calculate_summaries",
            side_effect=RuntimeError("boom"),
        ):
            _, _, _, summary = pipeline._step_technical_analysis(ohlcv)
        assert summary is None


# ---------------------------------------------------------------------------
# _step_pattern_recognition — exception in one func doesn't block others
# ---------------------------------------------------------------------------
class TestStepPatternRecognition:
    def test_single_func_failure_continues(self):
        chain = MagicMock()
        pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=chain)
        ohlcv = _make_ohlcv(30)
        failing_mock = MagicMock(side_effect=RuntimeError("boom"))
        failing_mock.__name__ = "detect_candlestick_patterns"
        with patch(
            "app.modules.pattern_recognition.candlestick.detect_candlestick_patterns",
            failing_mock,
        ):
            patterns = pipeline._step_pattern_recognition(ohlcv)
        # Other 4 detectors still ran; at minimum support_resistance should work
        assert isinstance(patterns, list)


# ---------------------------------------------------------------------------
# _step_fundamental_analysis — routing by instrument type
# ---------------------------------------------------------------------------
class TestStepFundamentalAnalysis:
    @pytest.mark.asyncio
    async def test_forex_routing(self):
        chain = MagicMock()
        pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=chain)
        mock_result = MagicMock()
        with patch(
            "app.modules.fundamental_analysis.forex.analyze_forex",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_fn:
            result = await pipeline._step_fundamental_analysis(InstrumentType.FOREX)
        mock_fn.assert_awaited_once_with("EURUSD")
        assert result is mock_result

    @pytest.mark.asyncio
    async def test_commodity_routing(self):
        chain = MagicMock()
        pipeline = AnalysisPipeline(symbol="GOLD", timeframe=Timeframe.H1, chain=chain)
        mock_result = MagicMock()
        with patch(
            "app.modules.fundamental_analysis.commodities.analyze_commodity",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_fn:
            result = await pipeline._step_fundamental_analysis(InstrumentType.COMMODITY)
        mock_fn.assert_awaited_once_with("GOLD")
        assert result is mock_result

    @pytest.mark.asyncio
    async def test_index_routing(self):
        chain = MagicMock()
        pipeline = AnalysisPipeline(symbol="US500", timeframe=Timeframe.H1, chain=chain)
        mock_result = MagicMock()
        with patch(
            "app.modules.fundamental_analysis.indices.analyze_index",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_fn:
            result = await pipeline._step_fundamental_analysis(InstrumentType.INDEX)
        mock_fn.assert_awaited_once_with("US500")
        assert result is mock_result

    @pytest.mark.asyncio
    async def test_unknown_instrument_returns_none(self):
        chain = MagicMock()
        pipeline = AnalysisPipeline(symbol="???", timeframe=Timeframe.H1, chain=chain)
        result = await pipeline._step_fundamental_analysis(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self):
        chain = MagicMock()
        pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=chain)
        with patch(
            "app.modules.fundamental_analysis.forex.analyze_forex",
            new_callable=AsyncMock,
            side_effect=RuntimeError("api down"),
        ):
            result = await pipeline._step_fundamental_analysis(InstrumentType.FOREX)
        assert result is None


# ---------------------------------------------------------------------------
# _persist_result — DB write + exception handling
# ---------------------------------------------------------------------------
class TestPersistResult:
    @pytest.mark.asyncio
    async def test_persist_success(self):
        chain = MagicMock()
        pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=chain)

        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.add = MagicMock()  # add() is sync

        mock_report = MagicMock()
        mock_report.model_dump_json.return_value = "{}"

        with patch("app.modules.pipeline.get_session_factory", return_value=mock_factory):
            await pipeline._persist_result(mock_report)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_persist_exception_handled(self):
        chain = MagicMock()
        pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=chain)

        mock_report = MagicMock()
        mock_report.model_dump_json.return_value = "{}"

        with patch("app.modules.pipeline.get_session_factory", side_effect=RuntimeError("no db")):
            # Should not raise — exception is caught and logged
            await pipeline._persist_result(mock_report)


# ---------------------------------------------------------------------------
# run() — outer exception handler
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pipeline_run_outer_exception():
    """When an unexpected exception occurs mid-pipeline, run() returns None and sets FAILED."""
    mock_chain = MagicMock()
    mock_chain.fetch_ohlcv = AsyncMock(return_value=_make_ohlcv(30))

    pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=mock_chain)

    with patch.object(pipeline, "_step_technical_analysis", side_effect=RuntimeError("unexpected")):
        report = await pipeline.run()

    assert report is None
    assert pipeline.status.status == AnalysisStatusType.FAILED


# ---------------------------------------------------------------------------
# _fetch_pivot_candle + D1 candle integration with pipeline
# ---------------------------------------------------------------------------
class TestFetchPivotCandle:
    @pytest.mark.asyncio
    async def test_fetch_pivot_candle_returns_candle(self):
        """_fetch_pivot_candle returns the previous completed daily candle."""
        daily = _make_ohlcv(5)
        chain = MagicMock()
        chain.fetch_ohlcv = AsyncMock(return_value=daily)
        pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=chain)

        result = await pipeline._fetch_pivot_candle()

        chain.fetch_ohlcv.assert_awaited_once_with("EURUSD", Timeframe.D1, "5d")
        assert result is daily[-2]

    @pytest.mark.asyncio
    async def test_fetch_pivot_candle_exception_returns_none(self):
        """_fetch_pivot_candle returns None on failure without crashing."""
        chain = MagicMock()
        chain.fetch_ohlcv = AsyncMock(side_effect=RuntimeError("network error"))
        pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=chain)

        result = await pipeline._fetch_pivot_candle()

        assert result is None

    def test_step_technical_analysis_uses_pivot_candle(self):
        """When pivot_candle is provided, it is used instead of ohlcv[-1]."""
        chain = MagicMock()
        pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=chain)
        ohlcv = _make_ohlcv(30)
        daily_candle = OHLCVData(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            open=1.1000,
            high=1.1200,
            low=1.0800,
            close=1.1100,
            volume=50000.0,
        )

        _, _, pp, _ = pipeline._step_technical_analysis(ohlcv, pivot_candle=daily_candle)

        assert len(pp) == 5
        classic = next(p for p in pp if p.type.value == "classic")
        # Verify using daily candle values, not ohlcv[-1]
        expected_pp = round((1.1200 + 1.0800 + 1.1100) / 3, 5)
        assert classic.pp == pytest.approx(expected_pp, abs=1e-4)

    def test_step_technical_analysis_fallback_when_no_pivot_candle(self):
        """When pivot_candle is None, falls back to ohlcv[-1]."""
        chain = MagicMock()
        pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.H1, chain=chain)
        ohlcv = _make_ohlcv(30)

        _, _, pp_with_none, _ = pipeline._step_technical_analysis(ohlcv, pivot_candle=None)
        _, _, pp_without, _ = pipeline._step_technical_analysis(ohlcv)

        assert len(pp_with_none) == 5
        assert pp_with_none[0].pp == pp_without[0].pp

    @pytest.mark.asyncio
    async def test_pipeline_d1_timeframe_uses_existing_ohlcv(self):
        """For D1 timeframe, pivot_candle comes from existing ohlcv — no extra fetch."""
        mock_chain = MagicMock()
        daily_data = _make_ohlcv(30)
        mock_chain.fetch_ohlcv = AsyncMock(return_value=daily_data)

        pipeline = AnalysisPipeline(symbol="EURUSD", timeframe=Timeframe.D1, chain=mock_chain)

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
        # Only one fetch_ohlcv call (for step 1 data), not two (no separate D1 fetch)
        assert mock_chain.fetch_ohlcv.await_count == 1

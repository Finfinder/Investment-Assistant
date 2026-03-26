"""Asynchronous analysis pipeline — orchestrates the full analysis flow."""

import logging
import uuid
from typing import TYPE_CHECKING

from cachetools import TTLCache

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.instrument_classifier import classify_instrument
from app.core.models import (
    AnalysisReport,
    AnalysisStatus,
    AnalysisStatusType,
    FundamentalData,
    IndicatorValue,
    InstrumentType,
    MovingAverage,
    OHLCVData,
    PatternDetection,
    PivotPoints,
    SignalSummary,
    Timeframe,
)
from app.modules.data_acquisition.fallback_chain import FallbackChainManager
from app.modules.data_acquisition.providers.yfinance_provider import YFinanceProvider

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.modules.data_acquisition.interfaces import DataProvider

logger = logging.getLogger(__name__)

# In-memory task tracking (TTL=1h, max 1000 entries to prevent memory leak)
analysis_tasks: TTLCache[str, AnalysisStatus] = TTLCache(maxsize=1000, ttl=3600)

PIPELINE_STEPS = [
    "Pobieranie danych",
    "Analiza techniczna",
    "Rozpoznawanie formacji",
    "Analiza fundamentalna",
    "Agregacja sygnalow",
    "Generowanie strategii",
]


def _build_chain() -> FallbackChainManager:
    """Build a fallback chain from configured providers."""
    settings = get_settings()
    providers: list[DataProvider] = [YFinanceProvider()]
    try:
        from app.modules.data_acquisition.providers.twelve_data_provider import TwelveDataProvider

        if settings.TWELVE_DATA_API_KEY:
            providers.append(TwelveDataProvider(api_key=settings.TWELVE_DATA_API_KEY))
    except ImportError:
        pass
    try:
        from app.modules.data_acquisition.providers.fmp_provider import FMPProvider

        if settings.FMP_API_KEY:
            providers.append(FMPProvider(api_key=settings.FMP_API_KEY))
    except ImportError:
        pass
    return FallbackChainManager(providers)


class AnalysisPipeline:
    """Runs through all analysis steps, tracks progress, and persists results."""

    def __init__(self, symbol: str, timeframe: Timeframe, chain: FallbackChainManager | None = None) -> None:
        self.analysis_id = str(uuid.uuid4())
        self.symbol = symbol
        self.timeframe = timeframe
        self._chain = chain or _build_chain()
        self._status = AnalysisStatus(
            id=self.analysis_id,
            status=AnalysisStatusType.PENDING,
            progress_pct=0.0,
            current_step="",
            steps_completed=[],
        )
        analysis_tasks[self.analysis_id] = self._status

    @property
    def status(self) -> AnalysisStatus:
        return self._status

    def _update_status(self, step_index: int, step_name: str) -> None:
        progress = (step_index / len(PIPELINE_STEPS)) * 100
        self._status.status = AnalysisStatusType.RUNNING
        self._status.progress_pct = min(progress, 99.0)
        self._status.current_step = step_name
        analysis_tasks[self.analysis_id] = self._status

    def _complete_step(self, step_name: str) -> None:
        self._status.steps_completed.append(step_name)

    def _fail(self, error: str) -> None:
        self._status.status = AnalysisStatusType.FAILED
        self._status.error_message = error
        analysis_tasks[self.analysis_id] = self._status

    async def run(self) -> AnalysisReport | None:
        """Execute the full 6-step pipeline.

        Returns AnalysisReport on success, None on complete failure.
        Partial failures are handled gracefully — individual steps may
        return empty results without blocking the pipeline.
        """
        try:
            # Step 1: Data fetch
            self._update_status(0, PIPELINE_STEPS[0])
            ohlcv = await self._step_fetch_data()
            self._complete_step(PIPELINE_STEPS[0])

            if not ohlcv:
                self._fail("Brak danych rynkowych dla podanego symbolu")
                return None

            # Step 2: Technical Analysis
            self._update_status(1, PIPELINE_STEPS[1])
            indicators, moving_averages, pivot_points, signal_summary = self._step_technical_analysis(ohlcv)
            self._complete_step(PIPELINE_STEPS[1])

            # Step 3: Pattern Recognition
            self._update_status(2, PIPELINE_STEPS[2])
            patterns = self._step_pattern_recognition(ohlcv)
            self._complete_step(PIPELINE_STEPS[2])

            # Step 4: Fundamental Analysis (graceful degradation)
            self._update_status(3, PIPELINE_STEPS[3])
            fundamental = await self._step_fundamental_analysis()
            self._complete_step(PIPELINE_STEPS[3])

            # Step 5: Signal Aggregation
            self._update_status(4, PIPELINE_STEPS[4])
            from app.modules.signal_aggregation.aggregator import SignalAggregator
            from app.modules.signal_aggregation.scoring import calculate_weighted_score, determine_direction

            aggregator = SignalAggregator(
                indicators=indicators,
                moving_averages=moving_averages,
                signal_summary=signal_summary,
                patterns=patterns,
                fundamental=fundamental,
            )
            score = calculate_weighted_score(aggregator)
            direction = determine_direction(score)
            self._complete_step(PIPELINE_STEPS[4])

            # Step 6: Strategy Generation & Report
            self._update_status(5, PIPELINE_STEPS[5])
            from app.modules.strategy_generator.report_builder import build_report

            report = build_report(
                symbol=self.symbol,
                timeframe=self.timeframe,
                ohlcv=ohlcv,
                indicators=indicators,
                moving_averages=moving_averages,
                pivot_points=pivot_points,
                patterns=patterns,
                signal_summary=signal_summary,
                fundamental=fundamental,
                direction=direction,
            )
            self._complete_step(PIPELINE_STEPS[5])

            # Persist result
            await self._persist_result(report)

            self._status.status = AnalysisStatusType.COMPLETED
            self._status.progress_pct = 100.0
            self._status.current_step = ""
            analysis_tasks[self.analysis_id] = self._status

            return report

        except Exception as exc:
            logger.exception("Pipeline failed for %s: %s", self.symbol, exc)
            self._fail(str(exc))
            return None

    async def _step_fetch_data(self) -> list[OHLCVData]:
        try:
            return await self._chain.fetch_ohlcv(self.symbol, self.timeframe, "90d")
        except Exception as exc:
            logger.warning("Data fetch failed: %s", exc)
            return []

    def _step_technical_analysis(
        self, ohlcv: list[OHLCVData]
    ) -> tuple[list[IndicatorValue], list[MovingAverage], list[PivotPoints], SignalSummary | None]:
        from app.modules.technical_analysis.indicators import calculate_indicators
        from app.modules.technical_analysis.moving_averages import calculate_moving_averages
        from app.modules.technical_analysis.pivot_points import calculate_pivot_points
        from app.modules.technical_analysis.summary import calculate_summaries

        try:
            indicators = calculate_indicators(ohlcv)
        except Exception as exc:
            logger.warning("Indicators calculation failed: %s", exc)
            indicators = []

        try:
            moving_averages = calculate_moving_averages(ohlcv)
        except Exception as exc:
            logger.warning("Moving averages calculation failed: %s", exc)
            moving_averages = []

        try:
            last = ohlcv[-1]
            pivot_points = calculate_pivot_points(last.high, last.low, last.close, last.open)
        except Exception as exc:
            logger.warning("Pivot points calculation failed: %s", exc)
            pivot_points = []

        try:
            signal_summary = calculate_summaries(indicators, moving_averages)
        except Exception as exc:
            logger.warning("Summary calculation failed: %s", exc)
            signal_summary = None

        return indicators, moving_averages, pivot_points, signal_summary

    def _step_pattern_recognition(self, ohlcv: list[OHLCVData]) -> list[PatternDetection]:
        from app.modules.pattern_recognition.candlestick import detect_candlestick_patterns
        from app.modules.pattern_recognition.chart_patterns import detect_chart_patterns
        from app.modules.pattern_recognition.fibonacci import calculate_fibonacci_levels
        from app.modules.pattern_recognition.iki_detector import detect_iki_pattern
        from app.modules.pattern_recognition.support_resistance import detect_support_resistance

        patterns: list[PatternDetection] = []
        funcs: list[Callable[[list[OHLCVData]], list[PatternDetection]]] = [
            detect_candlestick_patterns,
            detect_support_resistance,
            calculate_fibonacci_levels,
            detect_chart_patterns,
            detect_iki_pattern,
        ]
        for func in funcs:
            try:
                patterns.extend(func(ohlcv))
            except Exception as exc:
                logger.warning("Pattern detection (%s) failed: %s", func.__name__, exc)
        return patterns

    async def _step_fundamental_analysis(self) -> FundamentalData | None:
        instrument_type = classify_instrument(self.symbol)
        if instrument_type is None:
            return None

        try:
            if instrument_type == InstrumentType.FOREX:
                from app.modules.fundamental_analysis.forex import analyze_forex

                return analyze_forex(self.symbol)
            if instrument_type == InstrumentType.COMMODITY:
                from app.modules.fundamental_analysis.commodities import analyze_commodity

                return await analyze_commodity(self.symbol)
            from app.modules.fundamental_analysis.indices import analyze_index

            return analyze_index(self.symbol)
        except Exception as exc:
            logger.warning("Fundamental analysis failed for %s: %s", self.symbol, exc)
            return None

    async def _persist_result(self, report: AnalysisReport) -> None:
        """Save the analysis result to the database."""
        try:
            from app.core.database import AnalysisResult

            session_factory = get_session_factory()
            async with session_factory() as session:
                result = AnalysisResult(
                    id=self.analysis_id,
                    symbol=self.symbol,
                    timeframe=self.timeframe.value,
                    status="completed",
                    result_json=report.model_dump_json(),
                )
                session.add(result)
                await session.commit()
        except Exception as exc:
            logger.warning("Failed to persist analysis result: %s", exc)

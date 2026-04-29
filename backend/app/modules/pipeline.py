"""Asynchronous analysis pipeline — orchestrates the full analysis flow."""

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING

from cachetools import TTLCache

from app.core.database import get_session_factory
from app.core.instrument_classifier import classify_instrument
from app.core.models import (
    AnalysisReport,
    AnalysisStatus,
    AnalysisStatusType,
    AnalysisTimeframeContext,
    FundamentalData,
    IndicatorPreset,
    IndicatorValue,
    InstrumentType,
    LongTermTrend,
    MovingAverage,
    OHLCVData,
    PatternDetection,
    PivotPoints,
    SignalSummary,
    Timeframe,
)
from app.modules.data_acquisition.fallback_chain import FallbackChainManager, build_fallback_chain
from app.modules.data_acquisition.multi_timeframe import MultiTimeframeFetchBundle, MultiTimeframeFetcher
from app.modules.data_acquisition.timeframes import AnalysisTimeframePlan, DataTimeframe, resolve_analysis_timeframes
from app.modules.pattern_recognition.consolidator import consolidate_patterns
from app.modules.technical_analysis.long_term_trend import build_long_term_trend
from app.modules.technical_analysis.pivot_points import get_pivot_candle

if TYPE_CHECKING:
    from collections.abc import Callable


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


class AnalysisPipeline:
    """Runs through all analysis steps, tracks progress, and persists results."""

    def __init__(
        self,
        symbol: str,
        timeframe: Timeframe,
        chain: FallbackChainManager | None = None,
        preset: IndicatorPreset = IndicatorPreset.INVESTING,
    ) -> None:
        self.analysis_id = str(uuid.uuid4())
        self.symbol = symbol
        self.timeframe = timeframe
        self.timeframe_plan: AnalysisTimeframePlan = resolve_analysis_timeframes(timeframe)
        self.preset = preset
        self._chain = chain or build_fallback_chain()
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

    def complete(self) -> None:
        """Mark analysis as COMPLETED and publish to analysis_tasks.

        Must be called by the API layer AFTER caching the report
        in _analysis_results to prevent the race condition.
        """
        self._status.status = AnalysisStatusType.COMPLETED
        self._status.progress_pct = 100.0
        self._status.current_step = ""
        analysis_tasks[self.analysis_id] = self._status

    async def run(self) -> AnalysisReport | None:
        """Execute the full 6-step pipeline.

        Returns AnalysisReport on success, None on complete failure.
        Partial failures are handled gracefully — individual steps may
        return empty results without blocking the pipeline.
        """
        try:
            # Classify instrument once, reuse in fundamental analysis and report
            instrument_type = classify_instrument(self.symbol)

            # Step 1: Data fetch
            self._update_status(0, PIPELINE_STEPS[0])
            fetch_bundle = await self._step_fetch_data()
            ohlcv = fetch_bundle.main_ohlcv
            self._complete_step(PIPELINE_STEPS[0])

            if not ohlcv:
                self._fail("Brak danych rynkowych dla podanego symbolu")
                return None

            daily_ohlcv = fetch_bundle.get(DataTimeframe.D1)
            pivot_source = daily_ohlcv or ohlcv
            pivot_candle = get_pivot_candle(pivot_source)

            # Step 2: Technical Analysis (offload to thread — CPU-intensive)
            self._update_status(1, PIPELINE_STEPS[1])
            indicators, moving_averages, pivot_points, signal_summary = await asyncio.to_thread(
                self._step_technical_analysis, ohlcv, pivot_candle
            )
            long_term_trend = await asyncio.to_thread(
                self._step_long_term_trend,
                fetch_bundle.get(DataTimeframe.W1),
            )
            self._complete_step(PIPELINE_STEPS[1])

            # Step 3: Pattern Recognition (offload to thread — CPU-intensive)
            self._update_status(2, PIPELINE_STEPS[2])
            patterns = await asyncio.to_thread(self._step_pattern_recognition, ohlcv, self.timeframe)
            scanner_patterns = await asyncio.to_thread(
                self._step_multi_timeframe_pattern_recognition,
                fetch_bundle,
                patterns,
            )
            pattern_scanner_results = await asyncio.to_thread(consolidate_patterns, scanner_patterns)
            self._complete_step(PIPELINE_STEPS[2])

            # Step 4: Fundamental Analysis (graceful degradation)
            self._update_status(3, PIPELINE_STEPS[3])
            fundamental = await self._step_fundamental_analysis(instrument_type)
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
                timeframe_context=self._build_timeframe_context(),
                pattern_scanner_results=pattern_scanner_results,
                long_term_trend=long_term_trend,
                signal_summary=signal_summary,
                fundamental=fundamental,
                direction=direction,
                instrument_type=instrument_type,
            )
            self._complete_step(PIPELINE_STEPS[5])

            # Persist result
            await self._persist_result(report)

            # NOTE: COMPLETED status is NOT published here — the caller
            # (_run_pipeline in analysis.py) must call complete() AFTER
            # caching the report in _analysis_results to avoid the race
            # condition where WebSocket sends COMPLETED before the report
            # is available via GET /analysis/{id}.

            return report

        except Exception as exc:
            logger.exception("Pipeline failed for %s: %s", self.symbol, exc)
            self._fail(str(exc))
            return None

    async def _step_fetch_data(self) -> MultiTimeframeFetchBundle:
        try:
            session_factory = get_session_factory()
            fetcher = MultiTimeframeFetcher(self._chain, session_factory)
            return await fetcher.fetch(self.symbol, self.timeframe_plan)
        except Exception as exc:
            logger.warning("Data fetch failed: %s", exc)
            return MultiTimeframeFetchBundle(
                main_timeframe=self.timeframe_plan.main_timeframe,
                candles_by_timeframe={self.timeframe_plan.main_timeframe: []},
                errors={self.timeframe_plan.main_timeframe: str(exc)},
            )

    def _step_technical_analysis(
        self, ohlcv: list[OHLCVData], pivot_candle: OHLCVData | None = None
    ) -> tuple[list[IndicatorValue], list[MovingAverage], list[PivotPoints], SignalSummary | None]:
        from app.modules.technical_analysis.indicators import calculate_indicators
        from app.modules.technical_analysis.moving_averages import calculate_moving_averages
        from app.modules.technical_analysis.pivot_points import calculate_pivot_points
        from app.modules.technical_analysis.presets import get_preset_params
        from app.modules.technical_analysis.summary import calculate_summaries

        params = get_preset_params(self.preset)

        try:
            indicators = calculate_indicators(ohlcv, params)
        except Exception as exc:
            logger.warning("Indicators calculation failed: %s", exc)
            indicators = []

        try:
            moving_averages = calculate_moving_averages(ohlcv)
        except Exception as exc:
            logger.warning("Moving averages calculation failed: %s", exc)
            moving_averages = []

        try:
            candle = pivot_candle or ohlcv[-1]
            pivot_points = calculate_pivot_points(candle.high, candle.low, candle.close, candle.open)
        except Exception as exc:
            logger.warning("Pivot points calculation failed: %s", exc)
            pivot_points = []

        try:
            signal_summary = calculate_summaries(indicators, moving_averages)
        except Exception as exc:
            logger.warning("Summary calculation failed: %s", exc)
            signal_summary = None

        return indicators, moving_averages, pivot_points, signal_summary

    def _step_pattern_recognition(
        self,
        ohlcv: list[OHLCVData],
        timeframe: Timeframe | None = None,
    ) -> list[PatternDetection]:
        from app.modules.pattern_recognition.candlestick import detect_candlestick_patterns
        from app.modules.pattern_recognition.chart_patterns import detect_chart_patterns
        from app.modules.pattern_recognition.fibonacci import calculate_fibonacci_levels
        from app.modules.pattern_recognition.iki_detector import detect_iki_pattern
        from app.modules.pattern_recognition.relevance_scorer import calculate_target_prices, score_patterns
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

        # Wypełnij detected_at_timestamp z danych OHLCV
        for pattern in patterns:
            idx = pattern.detected_at_index if pattern.detected_at_index is not None else len(ohlcv) - 1
            idx = max(0, min(idx, len(ohlcv) - 1))
            pattern.detected_at_timestamp = ohlcv[idx].timestamp.isoformat()
            pattern.timeframe = timeframe

        # Oblicz target_price per formacja
        try:
            calculate_target_prices(patterns, ohlcv)
        except Exception as exc:
            logger.warning("calculate_target_prices failed: %s", exc)

        # Oblicz relevance_score per formacja
        try:
            current_price = float(ohlcv[-1].close)
            score_patterns(patterns, len(ohlcv), current_price)
        except Exception as exc:
            logger.warning("score_patterns failed: %s", exc)

        # Sortuj malejąco po relevance_score
        patterns.sort(key=lambda p: p.relevance_score, reverse=True)

        return patterns

    def _step_long_term_trend(self, weekly_ohlcv: list[OHLCVData]) -> LongTermTrend | None:
        return build_long_term_trend(weekly_ohlcv, self.preset)

    def _step_multi_timeframe_pattern_recognition(
        self,
        fetch_bundle: MultiTimeframeFetchBundle,
        main_patterns: list[PatternDetection],
    ) -> list[PatternDetection]:
        scanner_patterns: list[PatternDetection] = []

        for data_timeframe in self.timeframe_plan.pattern_scanner_timeframes:
            public_timeframe = data_timeframe.to_public()
            if public_timeframe is None:
                continue

            candles = fetch_bundle.get(data_timeframe)
            if not candles:
                continue

            if public_timeframe == self.timeframe:
                scanner_patterns.extend(main_patterns)
                continue

            scanner_patterns.extend(self._step_pattern_recognition(candles, public_timeframe))

        return scanner_patterns

    def _build_timeframe_context(self) -> AnalysisTimeframeContext:
        scanner_timeframes: list[Timeframe] = []
        for data_timeframe in self.timeframe_plan.pattern_scanner_timeframes:
            timeframe = data_timeframe.to_public()
            if timeframe is not None:
                scanner_timeframes.append(timeframe)

        return AnalysisTimeframeContext(
            pivot_points_timeframe=Timeframe.D1,
            pattern_scanner_timeframes=scanner_timeframes,
        )

    async def _step_fundamental_analysis(self, instrument_type: InstrumentType | None) -> FundamentalData | None:
        if instrument_type is None:
            return None

        try:
            if instrument_type == InstrumentType.FOREX:
                from app.modules.fundamental_analysis.forex import analyze_forex

                return await analyze_forex(self.symbol)
            if instrument_type == InstrumentType.COMMODITY:
                from app.modules.fundamental_analysis.commodities import analyze_commodity

                return await analyze_commodity(self.symbol)
            from app.modules.fundamental_analysis.indices import analyze_index

            return await analyze_index(self.symbol)
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

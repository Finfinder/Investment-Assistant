#!/usr/bin/env python3
"""Calibration runner for BULLISH_THRESHOLD and BEARISH_THRESHOLD thresholds.

This script:
1. Fetches historical OHLCV data for a representative basket of CFD instruments
2. Iterates through a rolling window of candles (training window)
3. For each window, runs the analysis pipeline to compute score and direction
4. Labels each signal with actual outcome (TP before SL, SL before TP, unknown)
5. Evaluates candidate threshold pairs
6. Generates a JSON report with metrics and recommendation

Usage:
    python -m scripts.calibrate_signal_thresholds --symbol EUR/USD --output report.json
    python -m scripts.calibrate_signal_thresholds --symbol-list basket.txt --output report.json
    python -m scripts.calibrate_signal_thresholds --real --symbol "^GSPC" --timeframe D1 --output real_report.json

The script does NOT modify thresholds in scoring.py. It only generates a report.
Threshold changes must be made manually by the development team after review.
"""

import argparse
import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.models import Direction, OHLCVData, PatternCategory
from app.modules.signal_aggregation.scoring import BEARISH_THRESHOLD, BULLISH_THRESHOLD
from app.modules.signal_aggregation.threshold_calibration import (
    CalibrationSample,
    CandidateMetrics,
    TransactionOutcome,
    evaluate_candidates,
    recommend_candidate,
)

logger = logging.getLogger(__name__)

# Default representative CFD basket for calibration
DEFAULT_SYMBOLS = [
    "EUR/USD",  # Major forex pair
    "GC=F",  # Gold commodity
    "^GSPC",  # S&P 500 index
]
DEFAULT_TIMEFRAMES = ["H1"]
DEFAULT_PERIOD = {
    "start": "synthetic",
    "end": "synthetic",
    "mode": "mvp_stub",
}

# yfinance period by timeframe (just below provider limits)
REAL_DATA_PERIOD: dict[str, str] = {
    "M15": "55d",
    "H1": "700d",
    "H4": "700d",
    "D1": "5y",
    "W1": "10y",
}

# Calibration configuration
CONFIG: dict[str, Any] = {
    "config_version": "mvp-2026-05-20",
    "symbols": DEFAULT_SYMBOLS,
    "timeframes": DEFAULT_TIMEFRAMES,
    "period": DEFAULT_PERIOD,
    "training_window_size": 100,  # Number of candles to use for score calculation
    "forward_window_size": 20,  # Number of future candles to check for SL/TP
    "step_size": None,  # Optional rolling step; when None it defaults to forward_window_size
    "candidate_pairs": [
        (0.10, -0.10),
        (0.15, -0.15),  # Current default
        (0.20, -0.20),
        (0.25, -0.25),
    ],
    "min_samples": 50,  # Minimum samples to generate report
}


def _iter_window_starts(total: int, training_size: int, forward_size: int, step_size: int) -> range:
    """Return rolling window starts for training/forward sampling."""
    return range(0, total - training_size - forward_size + 1, step_size)


def _detect_and_score_patterns_for_window(ohlcv: list[OHLCVData], timeframe: str) -> list[Any]:
    """Build pattern list and compute relevance_score using production pattern pipeline."""
    from app.modules.pattern_recognition.candlestick import detect_candlestick_patterns
    from app.modules.pattern_recognition.chart_patterns import detect_chart_patterns
    from app.modules.pattern_recognition.fibonacci import calculate_fibonacci_levels
    from app.modules.pattern_recognition.iki_detector import detect_iki_pattern
    from app.modules.pattern_recognition.relevance_scorer import calculate_target_prices, score_patterns
    from app.modules.pattern_recognition.support_resistance import detect_support_resistance

    patterns: list[Any] = []
    funcs = [
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

    if not patterns:
        return patterns

    for pattern in patterns:
        idx = pattern.detected_at_index if pattern.detected_at_index is not None else len(ohlcv) - 1
        idx = max(0, min(idx, len(ohlcv) - 1))
        pattern.detected_at_timestamp = ohlcv[idx].timestamp.isoformat()
        pattern.timeframe = timeframe

    try:
        calculate_target_prices(patterns, ohlcv)
    except Exception as exc:
        logger.warning("calculate_target_prices failed: %s", exc)

    try:
        current_price = float(ohlcv[-1].close)
        score_patterns(patterns, len(ohlcv), current_price)
    except Exception as exc:
        logger.warning("score_patterns failed: %s", exc)

    patterns.sort(key=lambda p: p.relevance_score, reverse=True)
    return patterns


def _build_sample_from_window(
    training: list[OHLCVData],
    future: list[OHLCVData],
    symbol: str,
    timeframe: str,
    sample_index: int,
) -> CalibrationSample:
    """Compute one calibration sample from training/future windows."""
    from app.modules.signal_aggregation.aggregator import SignalAggregator
    from app.modules.signal_aggregation.scoring import calculate_weighted_score, determine_direction
    from app.modules.signal_aggregation.threshold_calibration import label_signal_outcome
    from app.modules.strategy_generator.entry_calculator import calculate_entry_points
    from app.modules.strategy_generator.sl_tp_calculator import calculate_sl_tp
    from app.modules.technical_analysis.indicators import calculate_indicators
    from app.modules.technical_analysis.moving_averages import calculate_moving_averages
    from app.modules.technical_analysis.presets import IndicatorParams

    params = IndicatorParams()
    indicators = calculate_indicators(training, params)
    moving_averages = calculate_moving_averages(training)
    patterns = _detect_and_score_patterns_for_window(training, timeframe)

    aggregator = SignalAggregator(
        indicators=indicators,
        moving_averages=moving_averages,
        patterns=patterns,
        fundamental=None,
    )

    score = calculate_weighted_score(aggregator)
    direction: Direction | None = determine_direction(score)
    entry = training[-1].close

    stop_loss = None
    tp1 = None
    if direction is not None:
        sr_patterns = [pattern for pattern in patterns if pattern.category == PatternCategory.SUPPORT_RESISTANCE]
        entries = calculate_entry_points(training, direction, support_resistance=sr_patterns)
        if entries:
            entry_price = entries[0].get("price")
            if isinstance(entry_price, int | float):
                entry = float(entry_price)

        sl_tp = calculate_sl_tp(training, direction, entry, sr_patterns)
        stop_loss = sl_tp.get("stop_loss")
        tp1 = sl_tp.get("tp1")

    outcome = label_signal_outcome(direction, entry, stop_loss, tp1, future)
    return CalibrationSample(
        score=score,
        direction=direction,
        outcome=outcome,
        symbol=symbol,
        timeframe=timeframe,
        sample_index=sample_index,
    )


def _build_samples_from_ohlcv(
    ohlcv: list[OHLCVData],
    symbol: str,
    timeframe: str,
    training_size: int,
    forward_size: int,
    step_size: int,
) -> list[CalibrationSample]:
    """Build CalibrationSample list from a full OHLCV history using a rolling window.

    Args:
        ohlcv: Full chronological OHLCV list (oldest first).
        symbol: Instrument symbol for metadata.
        timeframe: Timeframe label for metadata.
        training_size: Number of candles per training window (used to compute score).
        forward_size: Number of future candles used to label TP/SL outcome.
        step_size: Candles to advance between windows. Use ``forward_size`` to
                   keep forward windows non-overlapping (avoids duplicate outcomes).

    Notes:
        - Fundamental data is excluded (not available point-in-time historically).
        - Pattern score is computed via production `score_patterns()` pipeline.
        - SL/TP levels are ATR-based and computed via `calculate_sl_tp()`.
    """
    samples: list[CalibrationSample] = []
    total = len(ohlcv)

    for i in _iter_window_starts(total, training_size, forward_size, step_size):
        training = ohlcv[i : i + training_size]
        future = ohlcv[i + training_size : i + training_size + forward_size]
        samples.append(
            _build_sample_from_window(
                training=training,
                future=future,
                symbol=symbol,
                timeframe=timeframe,
                sample_index=len(samples),
            )
        )

    return samples


class CalibrationRunner:
    """Runner for threshold calibration."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = self._merge_config(config)
        self.samples: list[CalibrationSample] = []

    def _resolve_step_size(self, forward_size: int) -> int:
        """Resolve rolling step size from config; default to forward window size."""
        configured = self.config.get("step_size")
        if isinstance(configured, int) and configured > 0:
            return configured
        return forward_size

    async def _build_samples_for_symbol_timeframe(
        self,
        provider: Any,
        symbol: str,
        tf_str: str,
        training_size: int,
        forward_size: int,
        step_size: int,
    ) -> list[CalibrationSample]:
        """Fetch OHLCV and build calibration samples for one symbol/timeframe pair."""
        from app.modules.data_acquisition.timeframes import DataTimeframe

        tf = DataTimeframe(tf_str)
        period = REAL_DATA_PERIOD.get(tf_str, "700d")
        logger.info("Fetching %s/%s period=%s", symbol, tf_str, period)
        ohlcv = await provider.fetch_ohlcv(symbol, tf, period)
        if not ohlcv:
            logger.warning("No data returned for %s/%s", symbol, tf_str)
            return []

        logger.info("Fetched %d candles for %s/%s — building samples", len(ohlcv), symbol, tf_str)
        samples = await asyncio.to_thread(
            _build_samples_from_ohlcv,
            ohlcv,
            symbol,
            tf_str,
            training_size,
            forward_size,
            step_size,
        )
        logger.info("Built %d samples for %s/%s", len(samples), symbol, tf_str)
        return samples

    async def _collect_real_samples(self, provider: Any) -> list[CalibrationSample]:
        """Collect samples for all configured symbol/timeframe combinations."""
        training_size: int = self.config["training_window_size"]
        forward_size: int = self.config["forward_window_size"]
        step_size = self._resolve_step_size(forward_size)
        all_samples: list[CalibrationSample] = []

        for symbol in self.config["symbols"]:
            for tf_str in self.config["timeframes"]:
                try:
                    samples = await self._build_samples_for_symbol_timeframe(
                        provider,
                        symbol,
                        tf_str,
                        training_size,
                        forward_size,
                        step_size,
                    )
                    all_samples.extend(samples)
                except Exception:
                    logger.exception("Failed to process %s/%s — skipping", symbol, tf_str)

        return all_samples

    @staticmethod
    def _apply_real_mode_report_adjustments(report: dict[str, Any]) -> None:
        """Adjust report metadata and limitations for real data mode."""
        current_period = dict(report["configuration"].get("period", {}))
        active_timeframes = report["configuration"].get("timeframes", [])
        report["configuration"]["mode"] = "real_data"
        report["configuration"]["period"] = {
            **current_period,
            "mode": "real_data",
            "per_timeframe_window": {tf: REAL_DATA_PERIOD.get(tf, "700d") for tf in active_timeframes},
        }
        report["limitations"] = [lim for lim in report["limitations"] if "synthetic training data" not in lim]

    async def run_with_real_data(self) -> dict[str, Any]:
        """Fetch real historical OHLCV via yfinance and compute calibration samples.

        Uses a rolling window approach:
        - Training window: last ``training_window_size`` candles → TA signals → score
        - Forward window: next ``forward_window_size`` candles → TP1/SL labeling
        - Step: configurable ``step_size`` candles; defaults to ``forward_window_size``

        Fundamental data is excluded — not available point-in-time for historical runs.
        Score is computed from technical analysis, moving averages and pattern pipeline
        with default production weights; candidate comparison remains relative and consistent.
        """
        from app.modules.data_acquisition.providers.yfinance_provider import YFinanceProvider

        provider = YFinanceProvider()
        self.samples = await self._collect_real_samples(provider)

        if not self.samples:
            logger.error("No samples generated from real data")
            return {"error": "No samples generated — check symbols and network connectivity"}

        min_samples: int = self.config.get("min_samples", 0)
        if len(self.samples) < min_samples:
            logger.warning(
                "Sample count %d is below minimum required %d — report may be statistically unreliable",
                len(self.samples),
                min_samples,
            )

        metrics_list = await asyncio.to_thread(self._evaluate_samples)
        recommendation = recommend_candidate(metrics_list)

        report = self._build_report(metrics_list, recommendation)
        self._apply_real_mode_report_adjustments(report)
        return report

    async def run_simple_stub(self) -> dict[str, Any]:
        """MVP stub: generates synthetic calibration report without live data.

        This stub is designed for testing the threshold calibration logic
        without external API dependencies. In production, this would be replaced
        with actual data fetching from yfinance or other providers.
        """
        logger.info("Running calibration with synthetic data (MVP stub)")

        self.samples = await asyncio.to_thread(self._generate_synthetic_samples)
        if not self.samples:
            logger.error("Failed to generate samples")
            return {"error": "No samples generated"}

        min_samples: int = self.config.get("min_samples", 0)
        if len(self.samples) < min_samples:
            logger.warning(
                "Sample count %d is below minimum required %d — report may be statistically unreliable",
                len(self.samples),
                min_samples,
            )

        metrics_list = await asyncio.to_thread(self._evaluate_samples)
        recommendation = recommend_candidate(metrics_list)

        report = self._build_report(metrics_list, recommendation)
        report["configuration"]["mode"] = "synthetic_stub"
        return report

    def _evaluate_samples(self) -> tuple[CandidateMetrics, ...]:
        """Evaluate configured threshold candidates against generated samples."""
        candidates: list[tuple[float, float]] = self.config["candidate_pairs"]
        return evaluate_candidates(self.samples, candidates)

    def _build_report(
        self,
        metrics_list: tuple[CandidateMetrics, ...],
        recommendation: CandidateMetrics | None,
    ) -> dict[str, Any]:
        """Build final calibration report payload."""
        config_version = str(self.config.get("config_version", "unknown"))
        period = self.config["period"]

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "version": "1.0",
            "configuration": {
                "config_version": config_version,
                "training_window_size": self.config["training_window_size"],
                "forward_window_size": self.config["forward_window_size"],
                "total_samples": len(self.samples),
                "symbols": self.config["symbols"],
                "timeframes": self.config["timeframes"],
                "period": period,
            },
            "baseline": self._select_baseline(metrics_list),
            "candidates": [self._metrics_to_dict(m) for m in metrics_list],
            "recommendation": self._build_recommendation(metrics_list, recommendation),
            "limitations": [
                "No transaction costs modeled.",
                "No slippage or spread considered.",
                "Results are from synthetic training data.",
                "Point-in-time fundamental data not available.",
                "Intrabar execution sequence not modeled.",
            ],
        }

    def _build_recommendation(
        self,
        metrics_list: tuple[CandidateMetrics, ...],
        recommendation: CandidateMetrics | None,
    ) -> dict[str, Any]:
        """Build recommendation section for calibration report."""
        action = self._recommendation_action(recommendation)
        symmetry = self._recommendation_symmetry(recommendation)

        return {
            "candidate_index": (
                metrics_list.index(recommendation) if recommendation and recommendation in metrics_list else -1
            ),
            "bullish_threshold": recommendation.bullish_threshold if recommendation else None,
            "bearish_threshold": recommendation.bearish_threshold if recommendation else None,
            "false_signal_rate": recommendation.false_signal_rate() if recommendation else None,
            "precision": recommendation.precision() if recommendation else None,
            "coverage": recommendation.coverage() if recommendation else None,
            "action": action,
            "symmetry": symmetry,
            "notes": "Recommendation based on minimizing false signal rate and maximizing coverage. "
            "Baseline is included for current thresholds from scoring.py.",
        }

    def _recommendation_action(self, recommendation: CandidateMetrics | None) -> str:
        """Describe whether the recommended candidate changes current production thresholds."""
        if recommendation is None:
            return "insufficient_data"

        if (
            recommendation.bullish_threshold == BULLISH_THRESHOLD
            and recommendation.bearish_threshold == BEARISH_THRESHOLD
        ):
            return "keep_current_thresholds"

        return "consider_threshold_change"

    def _recommendation_symmetry(self, recommendation: CandidateMetrics | None) -> str:
        """Describe whether the recommended thresholds are symmetric around zero."""
        if recommendation is None:
            return "unknown"

        if recommendation.bullish_threshold == abs(recommendation.bearish_threshold):
            return "symmetric"

        return "asymmetric"

    def _select_baseline(self, metrics_list: tuple[CandidateMetrics, ...]) -> dict[str, object]:
        """Select baseline metrics by current scoring thresholds, not by list index."""
        for metrics in metrics_list:
            if metrics.bullish_threshold == BULLISH_THRESHOLD and metrics.bearish_threshold == BEARISH_THRESHOLD:
                return self._metrics_to_dict(metrics)
        return {}

    def _merge_config(self, config: dict[str, Any] | None) -> dict[str, Any]:
        """Merge runtime config with defaults without mutating the module-level CONFIG."""
        merged = dict(CONFIG)
        if config is not None:
            merged.update(config)
        return merged

    def _generate_synthetic_samples(self) -> list[CalibrationSample]:
        """Generate synthetic calibration samples for testing."""
        samples = []
        # Synthetic data: various scores, directions, outcomes
        test_data = [
            (0.25, Direction.LONG, TransactionOutcome.TP_BEFORE_SL),
            (0.20, Direction.LONG, TransactionOutcome.TP_BEFORE_SL),
            (0.16, Direction.LONG, TransactionOutcome.SL_BEFORE_TP),
            (0.10, None, TransactionOutcome.UNKNOWN),
            (0.05, None, TransactionOutcome.UNKNOWN),
            (-0.05, None, TransactionOutcome.UNKNOWN),
            (-0.16, Direction.SHORT, TransactionOutcome.TP_BEFORE_SL),
            (-0.20, Direction.SHORT, TransactionOutcome.SL_BEFORE_TP),
            (-0.25, Direction.SHORT, TransactionOutcome.TP_BEFORE_SL),
            (0.30, Direction.LONG, TransactionOutcome.TP_BEFORE_SL),
            (0.22, Direction.LONG, TransactionOutcome.TP_BEFORE_SL),
            (0.18, Direction.LONG, TransactionOutcome.SL_BEFORE_TP),
            (0.12, None, TransactionOutcome.UNKNOWN),
            (-0.12, None, TransactionOutcome.UNKNOWN),
            (-0.18, Direction.SHORT, TransactionOutcome.TP_BEFORE_SL),
            (-0.22, Direction.SHORT, TransactionOutcome.SL_BEFORE_TP),
            (-0.30, Direction.SHORT, TransactionOutcome.TP_BEFORE_SL),
        ]

        for idx, (score, direction, outcome) in enumerate(test_data):
            samples.append(
                CalibrationSample(
                    score=score,
                    direction=direction,
                    outcome=outcome,
                    symbol="SYNTH/USD",
                    timeframe="H1",
                    sample_index=idx,
                )
            )

        return samples

    def _metrics_to_dict(self, metrics: CandidateMetrics) -> dict[str, object]:
        """Convert CandidateMetrics to dictionary."""
        return {
            "bullish_threshold": metrics.bullish_threshold,
            "bearish_threshold": metrics.bearish_threshold,
            "false_signal_rate": metrics.false_signal_rate(),
            "precision": metrics.precision(),
            "coverage": metrics.coverage(),
            "neutral_rate": metrics.neutral_rate(),
            "total_signals": metrics.total_signals,
            "long_signals": metrics.long_signals,
            "short_signals": metrics.short_signals,
            "neutral_signals": metrics.neutral_signals,
            "unknown_signals": metrics.unknown_signals,
            "long_tp_before_sl": metrics.long_tp_before_sl,
            "long_sl_before_tp": metrics.long_sl_before_tp,
            "short_tp_before_sl": metrics.short_tp_before_sl,
            "short_sl_before_tp": metrics.short_sl_before_tp,
        }


async def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Calibrate BULLISH_THRESHOLD and BEARISH_THRESHOLD thresholds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m scripts.calibrate_signal_thresholds --output report.json
    python -m scripts.calibrate_signal_thresholds --symbol EUR/USD --output report.json
    python -m scripts.calibrate_signal_thresholds --symbol-list basket.txt \
        --timeframe H1 --timeframe D1 --output report.json
        """,
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="Single symbol to calibrate (e.g. EUR/USD). Overrides the default basket in stub and --real modes.",
    )
    parser.add_argument(
        "--symbol-list",
        type=str,
        default=None,
        help="Path to a text file with one symbol per line. Overrides the default synthetic basket.",
    )
    parser.add_argument(
        "--timeframe",
        action="append",
        default=None,
        help="Timeframe label to include in the report. Can be passed multiple times.",
    )
    parser.add_argument(
        "--period-start",
        type=str,
        default=None,
        help="History period start label/date for the generated report metadata.",
    )
    parser.add_argument(
        "--period-end",
        type=str,
        default=None,
        help="History period end label/date for the generated report metadata.",
    )
    parser.add_argument(
        "--training-window-size",
        type=int,
        default=None,
        help="Override training window size used in calibration metadata.",
    )
    parser.add_argument(
        "--forward-window-size",
        type=int,
        default=None,
        help="Override forward window size used in calibration metadata.",
    )
    parser.add_argument(
        "--step-size",
        type=int,
        default=None,
        help="Override rolling window step size; defaults to forward-window-size when omitted.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="calibration_report.json",
        help="Output file for calibration report (JSON format)",
    )
    parser.add_argument(
        "--real",
        action="store_true",
        help="Fetch real historical OHLCV data via yfinance instead of using synthetic stub",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting calibration runner")

    runtime_config = await _build_runtime_config(args)
    runner = CalibrationRunner(config=runtime_config)

    # Run calibration: real data when --real flag is set, otherwise synthetic stub
    if args.real:
        logger.info("Mode: real historical data (yfinance)")
        report = await runner.run_with_real_data()
    else:
        logger.info("Mode: synthetic stub (use --real for live data)")
        report = await runner.run_simple_stub()

    # Save report
    output_path = Path(args.output)
    await asyncio.to_thread(_ensure_output_dir, output_path.parent)
    await asyncio.to_thread(_write_report_file, output_path, report)

    logger.info("Report saved to %s", output_path)

    # Print summary
    if "recommendation" in report:
        rec = report["recommendation"]
        print("\n=== Calibration Summary ===")
        print("Recommended thresholds:")
        print(f"  BULLISH_THRESHOLD: {rec['bullish_threshold']}")
        print(f"  BEARISH_THRESHOLD: {rec['bearish_threshold']}")
        print(f"  Action: {rec['action']}")
        print(f"  Symmetry: {rec['symmetry']}")
        print(_format_optional_percent("False signal rate", rec["false_signal_rate"]))
        print(_format_optional_percent("Precision", rec["precision"]))
        print(_format_optional_percent("Coverage", rec["coverage"]))


async def _build_runtime_config(args: argparse.Namespace) -> dict[str, Any]:
    """Build runtime configuration from CLI arguments."""
    symbols = await _resolve_symbols(args.symbol, args.symbol_list)
    timeframes = args.timeframe if args.timeframe else DEFAULT_TIMEFRAMES
    period = {
        "start": args.period_start or DEFAULT_PERIOD["start"],
        "end": args.period_end or DEFAULT_PERIOD["end"],
        "mode": DEFAULT_PERIOD["mode"],
    }

    runtime_config = dict(CONFIG)
    runtime_config["symbols"] = symbols
    runtime_config["timeframes"] = timeframes
    runtime_config["period"] = period

    if args.training_window_size is not None:
        runtime_config["training_window_size"] = args.training_window_size
    if args.forward_window_size is not None:
        runtime_config["forward_window_size"] = args.forward_window_size
    if args.step_size is not None:
        runtime_config["step_size"] = args.step_size

    return runtime_config


async def _resolve_symbols(symbol: str | None, symbol_list_path: str | None) -> list[str]:
    """Resolve symbol basket from CLI arguments."""
    if symbol is not None:
        return [symbol]
    if symbol_list_path is not None:
        return await asyncio.to_thread(_read_symbol_list, Path(symbol_list_path))
    return DEFAULT_SYMBOLS.copy()


def _read_symbol_list(symbol_list_path: Path) -> list[str]:
    """Read one symbol per line from a basket file."""
    with symbol_list_path.open() as file_handle:
        return [line.strip() for line in file_handle if line.strip()]


def _format_optional_percent(label: str, value: Any) -> str:
    """Format percentage metrics without hiding valid zero values."""
    if value is None:
        return f"  {label}: n/a"
    return f"  {label}: {value:.2%}"


def _ensure_output_dir(output_dir: Path) -> None:
    """Ensure output directory exists before report serialization."""
    output_dir.mkdir(parents=True, exist_ok=True)


def _write_report_file(output_path: Path, report: dict[str, Any]) -> None:
    """Persist report payload to disk."""
    with output_path.open("w") as file_handle:
        json.dump(report, file_handle, indent=2, default=str)


if __name__ == "__main__":
    asyncio.run(main())

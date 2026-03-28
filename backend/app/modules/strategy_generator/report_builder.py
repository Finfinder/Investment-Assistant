"""Report builder — composes AnalysisReport from all module results."""

from app.core.models import (
    AnalysisReport,
    Direction,
    FundamentalData,
    IndicatorValue,
    InstrumentType,
    MovingAverage,
    OHLCVData,
    PatternDetection,
    PivotPoints,
    SignalSummary,
    StrategyEntry,
    Timeframe,
)
from app.modules.strategy_generator.confidence_scorer import calculate_confidence
from app.modules.strategy_generator.entry_calculator import calculate_entry_points
from app.modules.strategy_generator.sl_tp_calculator import calculate_sl_tp


def build_report(
    symbol: str,
    timeframe: Timeframe,
    ohlcv: list[OHLCVData],
    indicators: list[IndicatorValue],
    moving_averages: list[MovingAverage],
    pivot_points: list[PivotPoints],
    patterns: list[PatternDetection],
    signal_summary: SignalSummary | None = None,
    fundamental: FundamentalData | None = None,
    direction: Direction | None = None,
    instrument_type: InstrumentType | None = None,
) -> AnalysisReport:
    """Build a complete AnalysisReport with strategies.

    Composes results from all modules, calculates entry/SL/TP for 2-3
    scenarios, and attaches confidence scores. Direction is determined
    externally by the signal aggregation module and passed in.
    """
    # Separate S/R and Fibonacci patterns
    sr_patterns = [p for p in patterns if p.pattern_type.startswith("S/R")]
    fib_patterns = [p for p in patterns if p.pattern_type.startswith("Fibonacci")]

    strategies: list[StrategyEntry] = []
    if direction is not None:
        strategies = _build_strategies(
            direction=direction,
            ohlcv=ohlcv,
            indicators=indicators,
            signal_summary=signal_summary,
            patterns=patterns,
            fundamental=fundamental,
            sr_patterns=sr_patterns,
            fib_patterns=fib_patterns,
        )

    return AnalysisReport(
        symbol=symbol,
        timeframe=timeframe,
        instrument_type=instrument_type,
        ohlcv_data=ohlcv,
        technical_indicators=indicators,
        moving_averages=moving_averages,
        pivot_points=pivot_points,
        patterns=patterns,
        fundamental=fundamental,
        signal_summary=signal_summary,
        strategies=strategies,
    )


def _build_strategies(
    direction: Direction,
    ohlcv: list[OHLCVData],
    indicators: list[IndicatorValue],
    signal_summary: SignalSummary | None,
    patterns: list[PatternDetection],
    fundamental: FundamentalData | None,
    sr_patterns: list[PatternDetection],
    fib_patterns: list[PatternDetection],
) -> list[StrategyEntry]:
    """Build 2-3 strategy scenarios with entry/SL/TP/confidence."""
    entries = calculate_entry_points(ohlcv, direction, sr_patterns, fib_patterns)
    strategies: list[StrategyEntry] = []

    for entry in entries:
        entry_price = float(entry["price"])  # type: ignore[arg-type]
        sl_tp = calculate_sl_tp(ohlcv, direction, entry_price, sr_patterns)
        confidence = calculate_confidence(
            direction=direction,
            indicators=indicators,
            signal_summary=signal_summary,
            patterns=patterns,
            fundamental=fundamental,
        )

        strategies.append(
            StrategyEntry(
                direction=direction,
                entry_condition=str(entry["condition"]),
                entry_price=entry_price,
                stop_loss=sl_tp["stop_loss"],
                tp1=sl_tp["tp1"],
                tp2=sl_tp["tp2"],
                confidence_pct=confidence,
            )
        )

    return strategies

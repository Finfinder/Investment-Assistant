"""Pure calibration logic for BULLISH_THRESHOLD and BEARISH_THRESHOLD.

This module provides isolated, testable functions for:
- Labeling historical signal outcomes (TP1 before SL, SL before TP1, unknown)
- Evaluating candidate threshold pairs against labeled samples
- Recommending threshold adjustments based on false signal rate and precision

The module MUST NOT import from other domain modules to maintain import boundary integrity.
Orchestration (combining with data providers, strategy generators, etc.) belongs in backend/scripts/.
"""

from enum import StrEnum

from app.core.models import Direction, OHLCVData


class TransactionOutcome(StrEnum):
    """Historical outcome of a signal in production."""

    TP_BEFORE_SL = "tp_before_sl"  # Take profit hit before stop loss (successful signal)
    SL_BEFORE_TP = "sl_before_tp"  # Stop loss hit before take profit (false signal)
    UNKNOWN = "unknown"  # Ambiguous or insufficient data


class CalibrationSample:
    """Single historical calibration data point."""

    __slots__ = (
        "direction",
        "outcome",
        "sample_index",
        "score",
        "symbol",
        "timeframe",
    )

    def __init__(
        self,
        score: float,
        direction: Direction | None,
        outcome: TransactionOutcome,
        symbol: str,
        timeframe: str,
        sample_index: int = 0,
    ) -> None:
        """Initialize a calibration sample.

        Args:
            score: Weighted signal score (-1.0..+1.0).
            direction: Direction classified by default thresholds (LONG, SHORT, or None).
            outcome: Actual historical result (TP_BEFORE_SL, SL_BEFORE_TP, UNKNOWN).
            symbol: Instrument symbol (e.g. 'EUR/USD').
            timeframe: Timeframe label (e.g. 'H1').
            sample_index: Sequential index for reference.
        """
        self.score = score
        self.direction = direction
        self.outcome = outcome
        self.symbol = symbol
        self.timeframe = timeframe
        self.sample_index = sample_index


class CandidateMetrics:
    """Metrics for a candidate threshold pair."""

    __slots__ = (
        "bearish_threshold",
        "bullish_threshold",
        "long_signals",
        "long_sl_before_tp",
        "long_tp_before_sl",
        "neutral_signals",
        "short_signals",
        "short_sl_before_tp",
        "short_tp_before_sl",
        "total_signals",
        "unknown_signals",
    )

    def __init__(
        self,
        bullish_threshold: float,
        bearish_threshold: float,
    ) -> None:
        """Initialize candidate metrics."""
        self.bullish_threshold = bullish_threshold
        self.bearish_threshold = bearish_threshold

        self.total_signals = 0
        self.long_signals = 0
        self.short_signals = 0
        self.neutral_signals = 0
        self.unknown_signals = 0

        self.long_tp_before_sl = 0
        self.long_sl_before_tp = 0
        self.short_tp_before_sl = 0
        self.short_sl_before_tp = 0

    def false_signal_rate(self) -> float:
        """Calculate false signal rate (SL before TP / total resolved signals)."""
        resolved = self.long_tp_before_sl + self.long_sl_before_tp + self.short_tp_before_sl + self.short_sl_before_tp
        if resolved == 0:
            return 0.0
        return (self.long_sl_before_tp + self.short_sl_before_tp) / resolved

    def precision(self) -> float:
        """Calculate precision (TP before SL / total resolved signals)."""
        resolved = self.long_tp_before_sl + self.long_sl_before_tp + self.short_tp_before_sl + self.short_sl_before_tp
        if resolved == 0:
            return 0.0
        return (self.long_tp_before_sl + self.short_tp_before_sl) / resolved

    def coverage(self) -> float:
        """Calculate coverage (resolved signals / total signals)."""
        if self.total_signals == 0:
            return 0.0
        resolved = self.long_tp_before_sl + self.long_sl_before_tp + self.short_tp_before_sl + self.short_sl_before_tp
        return resolved / self.total_signals

    def neutral_rate(self) -> float:
        """Calculate neutral rate (neutral + unknown / total signals)."""
        if self.total_signals == 0:
            return 0.0
        return (self.neutral_signals + self.unknown_signals) / self.total_signals

    def to_dict(self) -> dict[str, float | int]:
        """Export metrics as dictionary."""
        return {
            "bullish_threshold": self.bullish_threshold,
            "bearish_threshold": self.bearish_threshold,
            "total_signals": self.total_signals,
            "long_signals": self.long_signals,
            "short_signals": self.short_signals,
            "neutral_signals": self.neutral_signals,
            "unknown_signals": self.unknown_signals,
            "long_tp_before_sl": self.long_tp_before_sl,
            "long_sl_before_tp": self.long_sl_before_tp,
            "short_tp_before_sl": self.short_tp_before_sl,
            "short_sl_before_tp": self.short_sl_before_tp,
            "false_signal_rate": self.false_signal_rate(),
            "precision": self.precision(),
            "coverage": self.coverage(),
            "neutral_rate": self.neutral_rate(),
        }


def label_signal_outcome(
    direction: Direction | None,
    entry_price: float | None,
    stop_loss: float | None,
    tp1: float | None,
    future_ohlcv: list[OHLCVData] | None,
) -> TransactionOutcome:
    """Label a signal as TP before SL, SL before TP, or unknown.

    Args:
        direction: Signal direction (LONG, SHORT, or None).
        entry_price: Entry price for the signal.
        stop_loss: Stop loss level.
        tp1: Take profit 1 level.
        future_ohlcv: List of future OHLCV candles to check for SL/TP hits.
                      Candles must be sorted chronologically (oldest first).

    Returns:
        TransactionOutcome: The outcome classification.
    """
    # Require direction, prices, and future data
    if (
        direction is None
        or entry_price is None
        or stop_loss is None
        or tp1 is None
        or future_ohlcv is None
        or len(future_ohlcv) == 0
    ):
        return TransactionOutcome.UNKNOWN

    for candle in future_ohlcv:
        sl_hit = False
        tp_hit = False

        if direction == Direction.LONG:
            # For LONG: SL is hit when low <= SL, TP is hit when high >= TP
            sl_hit = candle.low <= stop_loss
            tp_hit = candle.high >= tp1
        elif direction == Direction.SHORT:
            # For SHORT: SL is hit when high >= SL, TP is hit when low <= TP
            sl_hit = candle.high >= stop_loss
            tp_hit = candle.low <= tp1

        # Both hit in same candle → ambiguous
        if sl_hit and tp_hit:
            return TransactionOutcome.UNKNOWN
        # TP hit first
        if tp_hit:
            return TransactionOutcome.TP_BEFORE_SL
        # SL hit first
        if sl_hit:
            return TransactionOutcome.SL_BEFORE_TP

    # No hit within future candles
    return TransactionOutcome.UNKNOWN


def evaluate_candidates(
    samples: list[CalibrationSample],
    candidates: list[tuple[float, float]],
) -> tuple[CandidateMetrics, ...]:
    """Evaluate multiple threshold candidate pairs against calibration samples.

    Args:
        samples: List of calibration samples with known outcomes.
        candidates: List of (bullish_threshold, bearish_threshold) tuples to evaluate.

    Returns:
        Tuple of CandidateMetrics, one for each candidate in order.
    """
    from app.modules.signal_aggregation.scoring import determine_direction

    results: list[CandidateMetrics] = []

    for bullish, bearish in candidates:
        metrics = CandidateMetrics(bullish, bearish)

        for sample in samples:
            classified_direction = determine_direction(
                sample.score,
                bullish_threshold=bullish,
                bearish_threshold=bearish,
            )
            _accumulate_metrics(metrics, classified_direction, sample.outcome)

        results.append(metrics)

    return tuple(results)


def _accumulate_metrics(
    metrics: CandidateMetrics,
    direction: Direction | None,
    outcome: TransactionOutcome,
) -> None:
    """Update candidate metrics for a single classified sample."""
    metrics.total_signals += 1
    _increment_direction_counter(metrics, direction)
    _increment_outcome_counter(metrics, direction, outcome)


def _increment_direction_counter(metrics: CandidateMetrics, direction: Direction | None) -> None:
    """Increment LONG/SHORT/neutral counters for classified direction."""
    if direction == Direction.LONG:
        metrics.long_signals += 1
    elif direction == Direction.SHORT:
        metrics.short_signals += 1
    else:
        metrics.neutral_signals += 1


def _increment_outcome_counter(
    metrics: CandidateMetrics,
    direction: Direction | None,
    outcome: TransactionOutcome,
) -> None:
    """Increment TP/SL/unknown counters only for actionable directions."""
    if direction is None:
        return

    if outcome == TransactionOutcome.UNKNOWN:
        metrics.unknown_signals += 1
        return

    if direction == Direction.LONG:
        if outcome == TransactionOutcome.TP_BEFORE_SL:
            metrics.long_tp_before_sl += 1
        else:
            metrics.long_sl_before_tp += 1
        return

    if outcome == TransactionOutcome.TP_BEFORE_SL:
        metrics.short_tp_before_sl += 1
    else:
        metrics.short_sl_before_tp += 1


def recommend_candidate(
    metrics_list: list[CandidateMetrics] | tuple[CandidateMetrics, ...],
) -> CandidateMetrics | None:
    """Recommend a candidate based on minimizing false signal rate and maximizing coverage.

    Strategy:
    - Prefer lower false signal rate (fewer SL before TP).
    - Among candidates with similar false signal rates, prefer higher coverage.
    - If no signals, return None.

    Args:
        metrics_list: List of CandidateMetrics to rank.

    Returns:
        The recommended CandidateMetrics, or None if list is empty.
    """
    if not metrics_list:
        return None

    # Filter out candidates with no resolved signals
    viable = [m for m in metrics_list if m.coverage() > 0.0]
    if not viable:
        return None

    # Sort by false signal rate (ascending), then by coverage (descending)
    viable.sort(key=lambda m: (m.false_signal_rate(), -m.coverage()))

    return viable[0]

"""Tests for signal_aggregation/threshold_calibration.py"""

import pytest

from app.core.models import Direction, OHLCVData
from app.modules.signal_aggregation.threshold_calibration import (
    CalibrationSample,
    CandidateMetrics,
    TransactionOutcome,
    evaluate_candidates,
    label_signal_outcome,
    recommend_candidate,
)


def _make_candles(prices: list[tuple[float, float, float, float]]) -> list[OHLCVData]:
    """Create OHLCV candles from (open, high, low, close) tuples."""
    from datetime import UTC, datetime, timedelta

    candles = []
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    for o, h, lo, c in prices:
        candles.append(
            OHLCVData(
                timestamp=ts,
                open=o,
                high=h,
                low=lo,
                close=c,
                volume=100.0,
            )
        )
        ts += timedelta(hours=1)
    return candles


class TestLabelSignalOutcome:
    """Test label_signal_outcome function."""

    def test_tp_before_sl_long(self):
        """LONG: TP1 hit before SL."""
        entry = 1.0500
        sl = 1.0400
        tp1 = 1.0600
        future = _make_candles(
            [
                (1.0500, 1.0550, 1.0480, 1.0530),  # No hit
                (1.0530, 1.0650, 1.0520, 1.0600),  # TP1 hit (high >= 1.0600)
            ]
        )
        outcome = label_signal_outcome(Direction.LONG, entry, sl, tp1, future)
        assert outcome == TransactionOutcome.TP_BEFORE_SL

    def test_sl_before_tp_long(self):
        """LONG: SL hit before TP1."""
        entry = 1.0500
        sl = 1.0400
        tp1 = 1.0600
        future = _make_candles(
            [
                (1.0500, 1.0520, 1.0350, 1.0400),  # SL hit (low <= 1.0400)
            ]
        )
        outcome = label_signal_outcome(Direction.LONG, entry, sl, tp1, future)
        assert outcome == TransactionOutcome.SL_BEFORE_TP

    def test_tp_before_sl_short(self):
        """SHORT: TP1 hit before SL."""
        entry = 1.0500
        sl = 1.0600
        tp1 = 1.0400
        future = _make_candles(
            [
                (1.0500, 1.0510, 1.0380, 1.0400),  # TP1 hit (low <= 1.0400)
            ]
        )
        outcome = label_signal_outcome(Direction.SHORT, entry, sl, tp1, future)
        assert outcome == TransactionOutcome.TP_BEFORE_SL

    def test_sl_before_tp_short(self):
        """SHORT: SL hit before TP1."""
        entry = 1.0500
        sl = 1.0600
        tp1 = 1.0400
        future = _make_candles(
            [
                (1.0500, 1.0650, 1.0450, 1.0600),  # SL hit (high >= 1.0600)
            ]
        )
        outcome = label_signal_outcome(Direction.SHORT, entry, sl, tp1, future)
        assert outcome == TransactionOutcome.SL_BEFORE_TP

    def test_both_hit_same_candle_unknown(self):
        """Both SL and TP hit in same candle → UNKNOWN."""
        entry = 1.0500
        sl = 1.0400
        tp1 = 1.0600
        future = _make_candles(
            [
                (1.0500, 1.0650, 1.0350, 1.0500),  # Both SL (low <= 1.0400) and TP1 (high >= 1.0600) hit
            ]
        )
        outcome = label_signal_outcome(Direction.LONG, entry, sl, tp1, future)
        assert outcome == TransactionOutcome.UNKNOWN

    def test_no_hit_unknown(self):
        """No SL or TP hit → UNKNOWN."""
        entry = 1.0500
        sl = 1.0400
        tp1 = 1.0600
        future = _make_candles(
            [
                (1.0500, 1.0550, 1.0480, 1.0530),
                (1.0530, 1.0560, 1.0500, 1.0550),
            ]
        )
        outcome = label_signal_outcome(Direction.LONG, entry, sl, tp1, future)
        assert outcome == TransactionOutcome.UNKNOWN

    def test_missing_direction_unknown(self):
        """Neutral direction (None) → UNKNOWN."""
        entry = 1.0500
        sl = 1.0400
        tp1 = 1.0600
        future = _make_candles([(1.0500, 1.0650, 1.0350, 1.0500)])
        outcome = label_signal_outcome(None, entry, sl, tp1, future)
        assert outcome == TransactionOutcome.UNKNOWN

    def test_missing_prices_unknown(self):
        """Missing entry, SL, or TP → UNKNOWN."""
        future = _make_candles([(1.0500, 1.0650, 1.0350, 1.0500)])
        assert label_signal_outcome(Direction.LONG, None, 1.0400, 1.0600, future) == TransactionOutcome.UNKNOWN
        assert label_signal_outcome(Direction.LONG, 1.0500, None, 1.0600, future) == TransactionOutcome.UNKNOWN
        assert label_signal_outcome(Direction.LONG, 1.0500, 1.0400, None, future) == TransactionOutcome.UNKNOWN

    def test_empty_future_candles_unknown(self):
        """Empty future candles → UNKNOWN."""
        outcome = label_signal_outcome(Direction.LONG, 1.0500, 1.0400, 1.0600, [])
        assert outcome == TransactionOutcome.UNKNOWN


class TestCandidateMetrics:
    """Test CandidateMetrics class."""

    def test_metrics_initialization(self):
        """CandidateMetrics initializes with zeros."""
        metrics = CandidateMetrics(0.2, -0.2)
        assert metrics.bullish_threshold == 0.2
        assert metrics.bearish_threshold == -0.2
        assert metrics.total_signals == 0
        assert metrics.false_signal_rate() == 0.0
        assert metrics.precision() == 0.0
        assert metrics.coverage() == 0.0

    def test_false_signal_rate(self):
        """False signal rate = (SL before TP) / resolved."""
        metrics = CandidateMetrics(0.15, -0.15)
        metrics.total_signals = 10
        metrics.long_tp_before_sl = 5
        metrics.long_sl_before_tp = 2
        metrics.short_tp_before_sl = 2
        metrics.short_sl_before_tp = 1

        # Resolved = 5 + 2 + 2 + 1 = 10
        # False = 2 + 1 = 3
        # FSR = 3 / 10 = 0.3
        assert metrics.false_signal_rate() == pytest.approx(0.3)

    def test_precision(self):
        """Precision = (TP before SL) / resolved."""
        metrics = CandidateMetrics(0.15, -0.15)
        metrics.long_tp_before_sl = 5
        metrics.long_sl_before_tp = 2
        metrics.short_tp_before_sl = 2
        metrics.short_sl_before_tp = 1

        # Resolved = 10
        # TP before SL = 5 + 2 = 7
        # Precision = 7 / 10 = 0.7
        assert metrics.precision() == pytest.approx(0.7)

    def test_coverage(self):
        """Coverage = resolved / total signals."""
        metrics = CandidateMetrics(0.15, -0.15)
        metrics.total_signals = 20
        metrics.long_tp_before_sl = 5
        metrics.long_sl_before_tp = 2
        metrics.short_tp_before_sl = 2
        metrics.short_sl_before_tp = 1
        metrics.unknown_signals = 10

        # Resolved = 10, Total = 20
        # Coverage = 10 / 20 = 0.5
        assert metrics.coverage() == pytest.approx(0.5)

    def test_neutral_rate(self):
        """Neutral rate = (neutral + unknown) / total."""
        metrics = CandidateMetrics(0.15, -0.15)
        metrics.total_signals = 20
        metrics.neutral_signals = 5
        metrics.unknown_signals = 5
        metrics.long_tp_before_sl = 5

        # Neutral rate = (5 + 5) / 20 = 0.5
        assert metrics.neutral_rate() == pytest.approx(0.5)

    def test_to_dict(self):
        """to_dict exports all metrics."""
        metrics = CandidateMetrics(0.2, -0.2)
        metrics.total_signals = 10
        metrics.long_signals = 3
        d = metrics.to_dict()
        assert d["bullish_threshold"] == 0.2
        assert d["bearish_threshold"] == -0.2
        assert d["total_signals"] == 10
        assert d["long_signals"] == 3


class TestEvaluateCandidates:
    """Test evaluate_candidates function."""

    def test_evaluate_single_candidate(self):
        """Evaluate one candidate against samples."""
        samples = [
            # score 0.2 > threshold 0.15 → LONG
            CalibrationSample(0.2, Direction.LONG, TransactionOutcome.TP_BEFORE_SL, "EUR/USD", "H1", 0),
            # score 0.16 > threshold 0.15 → LONG
            CalibrationSample(0.16, Direction.LONG, TransactionOutcome.SL_BEFORE_TP, "EUR/USD", "H1", 1),
            # score -0.2 < threshold -0.15 → SHORT
            CalibrationSample(-0.2, Direction.SHORT, TransactionOutcome.TP_BEFORE_SL, "EUR/USD", "H1", 2),
        ]

        candidates = [(0.15, -0.15)]
        results = evaluate_candidates(samples, candidates)

        assert len(results) == 1
        metrics = results[0]
        assert metrics.total_signals == 3
        assert metrics.long_signals == 2
        assert metrics.short_signals == 1
        assert metrics.long_tp_before_sl == 1
        assert metrics.long_sl_before_tp == 1
        assert metrics.short_tp_before_sl == 1

    def test_evaluate_multiple_candidates(self):
        """Evaluate multiple candidates."""
        samples = [
            CalibrationSample(0.2, Direction.LONG, TransactionOutcome.TP_BEFORE_SL, "EUR/USD", "H1", 0),
            CalibrationSample(0.1, Direction.LONG, TransactionOutcome.SL_BEFORE_TP, "EUR/USD", "H1", 1),
        ]

        candidates = [(0.15, -0.15), (0.25, -0.25), (0.05, -0.05)]
        results = evaluate_candidates(samples, candidates)

        assert len(results) == 3
        # With threshold 0.25: 0.2 < 0.25 → neutral, 0.1 < 0.25 → neutral
        assert results[1].long_signals == 0
        assert results[1].neutral_signals == 2

        # With threshold 0.05: 0.2 >= 0.05 → LONG, 0.1 >= 0.05 → LONG
        assert results[2].long_signals == 2

    def test_unknown_outcomes_not_counted_as_false(self):
        """UNKNOWN outcomes don't count toward false signal rate."""
        samples = [
            # score 0.2 > 0.15 → LONG with UNKNOWN outcome
            CalibrationSample(0.2, Direction.LONG, TransactionOutcome.UNKNOWN, "EUR/USD", "H1", 0),
            # score 0.16 > 0.15 → LONG with SL_BEFORE_TP outcome
            CalibrationSample(0.16, Direction.LONG, TransactionOutcome.SL_BEFORE_TP, "EUR/USD", "H1", 1),
        ]

        candidates = [(0.15, -0.15)]
        results = evaluate_candidates(samples, candidates)

        metrics = results[0]
        assert metrics.total_signals == 2
        assert metrics.unknown_signals == 1
        assert metrics.long_tp_before_sl == 0
        assert metrics.long_sl_before_tp == 1
        # Resolved = 1 (only the SL_BEFORE_TP)
        # FSR = 1 / 1 = 1.0
        assert metrics.false_signal_rate() == 1.0


class TestRecommendCandidate:
    """Test recommend_candidate function."""

    def test_recommend_lowest_false_signal_rate(self):
        """Recommendation prefers lowest false signal rate."""
        metrics1 = CandidateMetrics(0.15, -0.15)
        metrics1.total_signals = 10
        metrics1.long_tp_before_sl = 7
        metrics1.long_sl_before_tp = 3  # FSR = 0.3

        metrics2 = CandidateMetrics(0.20, -0.20)
        metrics2.total_signals = 10
        metrics2.long_tp_before_sl = 8
        metrics2.long_sl_before_tp = 2  # FSR = 0.2

        recommendation = recommend_candidate([metrics1, metrics2])
        assert recommendation is metrics2

    def test_recommend_highest_coverage_on_tie(self):
        """On FSR tie, recommend higher coverage."""
        metrics1 = CandidateMetrics(0.15, -0.15)
        metrics1.total_signals = 20
        metrics1.long_tp_before_sl = 5
        metrics1.long_sl_before_tp = 2
        metrics1.neutral_signals = 13  # Coverage = 7/20 = 0.35, FSR = 0.22..

        metrics2 = CandidateMetrics(0.20, -0.20)
        metrics2.total_signals = 20
        metrics2.long_tp_before_sl = 6
        metrics2.long_sl_before_tp = 2
        metrics2.neutral_signals = 12  # Coverage = 8/20 = 0.4, FSR = 0.25

        # Same FSR, so we take the one with better coverage
        metrics3 = CandidateMetrics(0.25, -0.25)
        metrics3.total_signals = 10
        metrics3.long_tp_before_sl = 6
        metrics3.long_sl_before_tp = 2
        metrics3.neutral_signals = 2  # Coverage = 8/10 = 0.8, FSR = 0.25 (same as metrics2)

        recommendation = recommend_candidate([metrics1, metrics2, metrics3])
        # metrics2 and metrics3 have same FSR (0.25), but metrics3 has higher coverage
        assert recommendation is metrics3

    def test_recommend_empty_list(self):
        """Empty list returns None."""
        recommendation = recommend_candidate([])
        assert recommendation is None

    def test_recommend_no_viable_candidates(self):
        """Candidates with zero coverage are excluded."""
        metrics1 = CandidateMetrics(0.50, -0.50)
        metrics1.total_signals = 10
        metrics1.neutral_signals = 10  # Coverage = 0

        recommendation = recommend_candidate([metrics1])
        assert recommendation is None

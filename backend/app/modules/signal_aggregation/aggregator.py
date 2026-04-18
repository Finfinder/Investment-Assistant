"""Signal aggregator — combines TA, pattern, and fundamental signals."""

from app.core.models import (
    RELIABILITY_MULTIPLIER,
    FundamentalData,
    IndicatorValue,
    MovingAverage,
    PatternDetection,
    SignalSummary,
    SignalType,
)

# Normalized signal scale: -1.0 (strong sell) to +1.0 (strong buy)
SIGNAL_SCORE: dict[SignalType, float] = {
    SignalType.STRONG_SELL: -1.0,
    SignalType.SELL: -0.5,
    SignalType.NEUTRAL: 0.0,
    SignalType.BUY: 0.5,
    SignalType.STRONG_BUY: 1.0,
}


class SignalAggregator:
    """Normalize and aggregate signals from TA, patterns, and fundamentals."""

    def __init__(
        self,
        indicators: list[IndicatorValue] | None = None,
        moving_averages: list[MovingAverage] | None = None,
        signal_summary: SignalSummary | None = None,
        patterns: list[PatternDetection] | None = None,
        fundamental: FundamentalData | None = None,
    ) -> None:
        self._indicators = indicators or []
        self._moving_averages = moving_averages or []
        self._signal_summary = signal_summary
        self._patterns = patterns or []
        self._fundamental = fundamental

    def normalize_ta_signal(self) -> float:
        """Normalize technical analysis signals to -1.0..+1.0.

        Uses the overall signal summary if available, otherwise averages
        individual indicator and MA signals.
        """
        if self._signal_summary:
            return SIGNAL_SCORE.get(self._signal_summary.overall_summary, 0.0)

        scores: list[float] = []
        for ind in self._indicators:
            scores.append(SIGNAL_SCORE.get(ind.signal, 0.0))
        for ma in self._moving_averages:
            scores.append(SIGNAL_SCORE.get(ma.sma_signal, 0.0))
            scores.append(SIGNAL_SCORE.get(ma.ema_signal, 0.0))

        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    def normalize_pattern_signal(self) -> float:
        """Normalize pattern detection signals to -1.0..+1.0.

        Bullish patterns contribute positive scores, bearish contribute negative.
        Weighted by confidence x reliability multiplier (★=1.0, ★★=1.3, ★★★=1.6).
        """
        if not self._patterns:
            return 0.0

        weighted_sum = 0.0
        total_weight = 0.0
        for p in self._patterns:
            direction = 1.0 if p.bullish else -1.0
            multiplier = RELIABILITY_MULTIPLIER.get(p.reliability, 1.0)
            effective_weight = p.confidence * multiplier
            weighted_sum += direction * effective_weight
            total_weight += effective_weight

        if total_weight == 0.0:
            return 0.0
        return max(-1.0, min(1.0, weighted_sum / total_weight))

    def normalize_fundamental_signal(self) -> float:
        """Normalize fundamental analysis score to -1.0..+1.0.

        FundamentalData.score is already -100..+100, just scale to -1..+1.
        """
        if self._fundamental is None:
            return 0.0
        return self._fundamental.score / 100.0

    def get_all_signals(self) -> dict[str, float]:
        """Return all normalized signals as a dict."""
        return {
            "technical_analysis": self.normalize_ta_signal(),
            "patterns": self.normalize_pattern_signal(),
            "fundamental": self.normalize_fundamental_signal(),
        }

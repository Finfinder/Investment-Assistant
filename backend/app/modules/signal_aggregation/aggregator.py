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


def _pattern_strength(pattern: PatternDetection) -> float:
    """Return the contextual strength of a pattern (0.0..1.0).

    Uses relevance_score as the primary measure when it has been computed
    (value > 0.0). Falls back to confidence when relevance_score equals
    the default 0.0, preserving expected behaviour for manually created
    PatternDetection objects and for patterns that bypassed score_patterns().
    """
    return pattern.relevance_score if pattern.relevance_score > 0.0 else pattern.confidence


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
        The signed contribution of each pattern is `direction * strength * multiplier`,
        where strength is determined by relevance_score (when > 0.0) or confidence
        as a fallback. The result is normalized by the sum of maximum possible weights
        (assuming full strength = 1.0 per pattern), so that a low-relevance pattern
        produces a proportionally weaker signal rather than a saturated ±1.0.

        Each pattern's contribution is additionally scaled by the reliability
        multiplier (★=1.0, ★★=1.3, ★★★=1.6), which acts as an independent
        quality amplifier separate from relevance_score.
        """
        if not self._patterns:
            return 0.0

        weighted_sum = 0.0
        total_max_weight = 0.0
        for p in self._patterns:
            direction = 1.0 if p.bullish else -1.0
            multiplier = RELIABILITY_MULTIPLIER.get(p.reliability, 1.0)
            effective_weight = _pattern_strength(p) * multiplier
            weighted_sum += direction * effective_weight
            total_max_weight += multiplier  # normalise by max possible weight (strength = 1.0)

        return max(-1.0, min(1.0, weighted_sum / total_max_weight))

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

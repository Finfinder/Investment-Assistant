from app.core.models import PatternCategory, PatternDetection, Timeframe
from app.modules.pattern_recognition.consolidator import consolidate_patterns


def _make_pattern(
    pattern_type: str,
    timeframe: Timeframe,
    bullish: bool = True,
    relevance_score: float = 0.5,
    confidence: float = 0.6,
) -> PatternDetection:
    return PatternDetection(
        pattern_type=pattern_type,
        confidence=confidence,
        bullish=bullish,
        category=PatternCategory.CANDLESTICK,
        timeframe=timeframe,
        relevance_score=relevance_score,
        reliability=2,
        description=f"{pattern_type} on {timeframe}",
    )


def test_consolidate_patterns_groups_duplicates_across_timeframes() -> None:
    patterns = [
        _make_pattern("Hammer", Timeframe.H1, relevance_score=0.4),
        _make_pattern("Hammer", Timeframe.D1, relevance_score=0.9),
        _make_pattern("Doji", Timeframe.M15, confidence=0.7),
    ]

    results = consolidate_patterns(patterns)

    assert len(results) == 2
    assert results[0].pattern_type == "Hammer"
    assert results[0].timeframes == [Timeframe.D1, Timeframe.H1]
    assert results[0].representative_pattern.timeframe == Timeframe.D1
    assert results[1].pattern_type == "Doji"
    assert results[1].timeframes == [Timeframe.M15]


def test_consolidate_patterns_separates_direction() -> None:
    patterns = [
        _make_pattern("Engulfing", Timeframe.H1, bullish=True),
        _make_pattern("Engulfing", Timeframe.D1, bullish=False),
    ]

    results = consolidate_patterns(patterns)

    assert len(results) == 2
    assert {result.bullish for result in results} == {True, False}

from app.core.models import PatternDetection, PatternScannerResult, Timeframe

_TIMEFRAME_ORDER = {
    Timeframe.D1: 0,
    Timeframe.H1: 1,
    Timeframe.M15: 2,
}


def _pick_representative_pattern(patterns: list[PatternDetection]) -> PatternDetection:
    return max(
        patterns,
        key=lambda pattern: (pattern.relevance_score, pattern.confidence, pattern.reliability),
    )


def consolidate_patterns(patterns: list[PatternDetection]) -> list[PatternScannerResult]:
    grouped: dict[tuple[str, str, bool], list[PatternDetection]] = {}

    for pattern in patterns:
        if pattern.timeframe is None:
            continue

        key = (pattern.pattern_type, pattern.category.value, pattern.bullish)
        grouped.setdefault(key, []).append(pattern)

    results: list[PatternScannerResult] = []
    for grouped_patterns in grouped.values():
        representative = _pick_representative_pattern(grouped_patterns)
        timeframes = sorted(
            {pattern.timeframe for pattern in grouped_patterns if pattern.timeframe is not None},
            key=lambda timeframe: _TIMEFRAME_ORDER.get(timeframe, len(_TIMEFRAME_ORDER)),
        )
        results.append(
            PatternScannerResult(
                pattern_type=representative.pattern_type,
                category=representative.category,
                bullish=representative.bullish,
                confidence=representative.confidence,
                timeframes=timeframes,
                representative_pattern=representative,
            )
        )

    return sorted(
        results,
        key=lambda result: (
            result.representative_pattern.relevance_score,
            result.confidence,
            result.representative_pattern.reliability,
        ),
        reverse=True,
    )

"""Relevance scoring and target price calculation for pattern detections."""

import logging
import re

import numpy as np

from app.core.models import OHLCVData, PatternCategory, PatternDetection

logger = logging.getLogger(__name__)

_FIBO_PRICE_RE = re.compile(r"at\s+([\d.]+)")
_SR_PRICE_RE = re.compile(r"price_([\d.]+)")


def score_patterns(patterns: list[PatternDetection], total_candles: int, current_price: float = 0.0) -> None:
    """Oblicza relevance_score w miejscu dla każdej formacji na liście.

    Wzór:
        relevance = 0.5 * confidence + 0.35 * recency + 0.15 * proximity

    Gdzie:
        recency   = 1 - (candles_since / total_candles)
                    candles_since = total_candles - 1 - detected_at_index
        proximity = 1 - min(1, |current_price - pattern_price| / price_range)
                    (tylko S/R i Fibonacci; dla reszty = 1.0)
    """
    if not patterns or total_candles <= 0:
        return

    for pattern in patterns:
        index = pattern.detected_at_index if pattern.detected_at_index is not None else total_candles - 1
        candles_since = total_candles - 1 - index
        recency = max(0.0, 1.0 - candles_since / total_candles)

        proximity = _calculate_proximity(pattern, current_price)

        score = 0.5 * pattern.confidence + 0.35 * recency + 0.15 * proximity
        pattern.relevance_score = round(min(1.0, max(0.0, score)), 4)


def _proximity_from_level(current_price: float, level_price: float) -> float:
    """Proximity = 1 - min(1, |current - level| / (5% * current))."""
    price_range = current_price * 0.05
    if price_range == 0:
        return 1.0
    return max(0.0, 1.0 - min(1.0, abs(current_price - level_price) / price_range))


def _extract_level_price(regex: re.Pattern[str], text: str) -> float | None:
    """Wyciąga cenę poziomu z tekstu za pomocą regex."""
    m = regex.search(text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _calculate_proximity(pattern: PatternDetection, current_price: float) -> float:
    """Oblicza komponent bliskości cenowej (proximity) dla formacji S/R i Fibonacci."""
    if current_price <= 0:
        return 1.0

    if pattern.category == PatternCategory.SUPPORT_RESISTANCE:
        level_price = _extract_level_price(_SR_PRICE_RE, pattern.location)
        return _proximity_from_level(current_price, level_price) if level_price is not None else 1.0

    if pattern.category == PatternCategory.FIBONACCI:
        level_price = _extract_level_price(_FIBO_PRICE_RE, pattern.description)
        return _proximity_from_level(current_price, level_price) if level_price is not None else 1.0

    return 1.0


def calculate_target_prices(patterns: list[PatternDetection], ohlcv: list[OHLCVData]) -> None:
    """Oblicza target_price w miejscu dla każdej formacji.

    Heurystyki per kategoria:
    - CANDLESTICK:        current_price +/- ATR(14) * 1.5
    - CHART_PATTERN:      current_price +/- wysokosc kanalu formacji (approx ATR * 2)
    - FIBONACCI:          cena poziomu fibo wyciągnięta z description
    - SUPPORT_RESISTANCE: cena poziomu wyciągnięta z location
    - IKI:                current_price +/- ATR(14) * 2
    """
    if not patterns or not ohlcv:
        return

    current_price = float(ohlcv[-1].close)
    atr = _calculate_atr14(ohlcv)

    for pattern in patterns:
        try:
            pattern.target_price = _target_for_pattern(pattern, current_price, atr)
        except Exception:
            logger.debug("Nie udało się obliczyć target_price dla %s", pattern.pattern_type)
            pattern.target_price = None


def _target_for_pattern(
    pattern: PatternDetection,
    current_price: float,
    atr: float,
) -> float | None:
    """Zwraca szacowany cel cenowy dla danej formacji."""
    direction = 1 if pattern.bullish else -1

    if pattern.category in (PatternCategory.CANDLESTICK, PatternCategory.CHART_PATTERN, PatternCategory.IKI):
        if atr <= 0:
            return None
        multiplier = 1.5 if pattern.category == PatternCategory.CANDLESTICK else 2.0
        return round(current_price + direction * atr * multiplier, 6)

    if pattern.category == PatternCategory.FIBONACCI:
        level = _extract_level_price(_FIBO_PRICE_RE, pattern.description)
        return round(level, 6) if level is not None else None

    if pattern.category == PatternCategory.SUPPORT_RESISTANCE:
        level = _extract_level_price(_SR_PRICE_RE, pattern.location)
        return round(level, 6) if level is not None else None

    return None


def _calculate_atr14(ohlcv: list[OHLCVData]) -> float:
    """Oblicza ATR(14) z listy danych OHLCV."""
    period = 14
    n = len(ohlcv)
    if n < period + 1:
        return 0.0

    highs = np.array([c.high for c in ohlcv], dtype=np.float64)
    lows = np.array([c.low for c in ohlcv], dtype=np.float64)
    closes = np.array([c.close for c in ohlcv], dtype=np.float64)

    tr = np.empty(n - 1, dtype=np.float64)
    for i in range(1, n):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr[i - 1] = max(hl, hc, lc)

    return float(np.mean(tr[-period:]))

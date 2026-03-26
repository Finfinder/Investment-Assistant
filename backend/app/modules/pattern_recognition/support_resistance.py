"""Support and Resistance level detection."""

import numpy as np
from scipy.signal import argrelextrema

from app.core.models import OHLCVData, PatternDetection


def detect_support_resistance(
    ohlcv: list[OHLCVData],
    order: int = 5,
    cluster_tolerance_pct: float = 0.5,
) -> list[PatternDetection]:
    """Identify support and resistance levels from historical price data.

    Uses local extrema detection and clusters nearby levels together.
    Also checks for bounces off EMA 50 and EMA 200.

    Args:
        ohlcv: OHLCV price data.
        order: Number of points on each side to compare for extrema detection.
        cluster_tolerance_pct: Percentage tolerance for clustering nearby levels.
    """
    if len(ohlcv) < order * 2 + 1:
        return []

    highs = np.array([c.high for c in ohlcv], dtype=np.float64)
    lows = np.array([c.low for c in ohlcv], dtype=np.float64)
    closes = np.array([c.close for c in ohlcv], dtype=np.float64)

    # Find local maxima (resistance) and minima (support)
    resistance_idx = argrelextrema(highs, np.greater_equal, order=order)[0]
    support_idx = argrelextrema(lows, np.less_equal, order=order)[0]

    raw_levels: list[tuple[float, bool]] = []  # (price, is_resistance)
    for idx in resistance_idx:
        raw_levels.append((float(highs[idx]), True))
    for idx in support_idx:
        raw_levels.append((float(lows[idx]), False))

    # Cluster nearby levels
    clustered = _cluster_levels(raw_levels, cluster_tolerance_pct)

    # Score each level by number of touches
    current_price = float(closes[-1])
    results: list[PatternDetection] = []

    for level_price, is_resistance, touch_count in clustered:
        strength = min(1.0, touch_count / 5.0)
        level_type = "resistance" if is_resistance else "support"
        distance_pct = abs(current_price - level_price) / current_price * 100

        desc = (
            f"{level_type.capitalize()} at {level_price:.2f} "
            f"({touch_count} touches, {distance_pct:.1f}% from current price)"
        )
        results.append(
            PatternDetection(
                pattern_type=f"S/R Level ({level_type})",
                confidence=round(strength, 2),
                description=desc,
                location=f"price_{level_price:.2f}",
                bullish=not is_resistance,
            )
        )

    # EMA bounces
    ema_patterns = _detect_ema_bounces(closes, current_price)
    results.extend(ema_patterns)

    return results


def _cluster_levels(
    levels: list[tuple[float, bool]],
    tolerance_pct: float,
) -> list[tuple[float, bool, int]]:
    """Cluster nearby price levels together.

    Returns list of (price, is_resistance, touch_count).
    """
    if not levels:
        return []

    sorted_levels = sorted(levels, key=lambda x: x[0])
    clusters: list[list[tuple[float, bool]]] = [[sorted_levels[0]]]

    for price, is_res in sorted_levels[1:]:
        cluster_avg = np.mean([p for p, _ in clusters[-1]])
        if abs(price - cluster_avg) / cluster_avg * 100 <= tolerance_pct:
            clusters[-1].append((price, is_res))
        else:
            clusters.append([(price, is_res)])

    result: list[tuple[float, bool, int]] = []
    for cluster in clusters:
        avg_price = float(np.mean([p for p, _ in cluster]))
        # Majority vote for resistance/support
        res_count = sum(1 for _, is_r in cluster if is_r)
        is_resistance = res_count >= len(cluster) / 2
        result.append((round(avg_price, 4), is_resistance, len(cluster)))

    return result


def _detect_ema_bounces(closes: np.ndarray, current_price: float) -> list[PatternDetection]:
    """Detect if price is near EMA 50 or EMA 200."""
    results: list[PatternDetection] = []
    n = len(closes)

    for period in (50, 200):
        if n < period:
            continue

        multiplier = 2.0 / (period + 1)
        ema = np.empty(n, dtype=np.float64)
        ema[0] = closes[0]
        for i in range(1, n):
            ema[i] = closes[i] * multiplier + ema[i - 1] * (1 - multiplier)

        ema_val = float(ema[-1])
        distance_pct = abs(current_price - ema_val) / ema_val * 100

        # Price within 1% of EMA is considered a "bounce zone"
        if distance_pct <= 1.0:
            bullish = current_price >= ema_val
            results.append(
                PatternDetection(
                    pattern_type=f"EMA {period} Bounce",
                    confidence=round(0.6 + (1.0 - distance_pct) * 0.3, 2),
                    description=(
                        f"Price near EMA {period} ({ema_val:.2f}), "
                        f"potential {'support' if bullish else 'resistance'}"
                    ),
                    location=f"ema_{period}",
                    bullish=bullish,
                )
            )

    return results

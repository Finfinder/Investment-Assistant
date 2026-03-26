"""Fibonacci retracement level calculator."""

import numpy as np
from scipy.signal import argrelextrema

from app.core.models import OHLCVData, PatternDetection

FIBO_LEVELS = (0.236, 0.382, 0.5, 0.618, 0.786)


def calculate_fibonacci_levels(
    ohlcv: list[OHLCVData],
    proximity_pct: float = 1.0,
) -> list[PatternDetection]:
    """Calculate Fibonacci retracement levels on the last significant swing.

    Uses argrelextrema to find the most recent swing high and swing low,
    then computes 5 Fibonacci retracement levels. Marks levels as "active"
    when the current price is within proximity_pct.

    Args:
        ohlcv: OHLCV price data (minimum 20 candles).
        proximity_pct: Percentage threshold for marking a level as active.
    """
    if len(ohlcv) < 20:
        return []

    highs = np.array([c.high for c in ohlcv], dtype=np.float64)
    lows = np.array([c.low for c in ohlcv], dtype=np.float64)

    swing_high_idx = argrelextrema(highs, np.greater_equal, order=5)[0]
    swing_low_idx = argrelextrema(lows, np.less_equal, order=5)[0]

    if len(swing_high_idx) == 0 or len(swing_low_idx) == 0:
        return []

    # Use the last swing high and swing low
    last_high_idx = int(swing_high_idx[-1])
    last_low_idx = int(swing_low_idx[-1])
    swing_high = float(highs[last_high_idx])
    swing_low = float(lows[last_low_idx])

    if swing_high == swing_low:
        return []

    # Determine direction: uptrend retracement if swing low came before swing high
    is_uptrend = last_low_idx < last_high_idx

    current_price = float(ohlcv[-1].close)
    results: list[PatternDetection] = []

    for level in FIBO_LEVELS:
        if is_uptrend:
            fibo_price = swing_high - level * (swing_high - swing_low)
        else:
            fibo_price = swing_low + level * (swing_high - swing_low)

        distance_pct = abs(current_price - fibo_price) / current_price * 100
        active = distance_pct <= proximity_pct

        results.append(
            PatternDetection(
                pattern_type=f"Fibonacci {level * 100:.1f}%",
                confidence=round(0.8 if active else 0.5, 2),
                description=(
                    f"{'Uptrend' if is_uptrend else 'Downtrend'} retracement "
                    f"{level * 100:.1f}% at {fibo_price:.2f}"
                    f"{' (ACTIVE)' if active else ''}"
                ),
                location=f"fibo_{level * 100:.1f}",
                bullish=is_uptrend,
            )
        )

    return results

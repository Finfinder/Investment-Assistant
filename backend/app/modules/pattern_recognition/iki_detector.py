"""IKI (Impuls-Korekta-Impuls) pattern detector."""

import numpy as np
import numpy.typing as npt

from app.core.models import OHLCVData, PatternCategory, PatternDetection

FIBO_RETRACEMENT_MIN = 0.382
FIBO_RETRACEMENT_MAX = 0.618
ATR_IMPULSE_MULTIPLIER = 2.0


def detect_iki_pattern(
    ohlcv: list[OHLCVData],
    atr_period: int = 14,
) -> list[PatternDetection]:
    """Detect Impuls-Korekta-Impuls (IKI) pattern.

    Criteria:
    1. Impulse: price move > 2 x ATR(14) in one direction
    2. Correction: retracement 38.2-61.8% Fibonacci of the impulse
    3. Second impulse: move in the same direction as the first

    Args:
        ohlcv: OHLCV price data (minimum atr_period + 20 candles).
        atr_period: ATR period for impulse size threshold.
    """
    min_candles = atr_period + 20
    if len(ohlcv) < min_candles:
        return []

    highs = np.array([c.high for c in ohlcv], dtype=np.float64)
    lows = np.array([c.low for c in ohlcv], dtype=np.float64)
    closes = np.array([c.close for c in ohlcv], dtype=np.float64)

    atr = _calculate_atr(highs, lows, closes, atr_period)
    if atr <= 0:
        return []

    results: list[PatternDetection] = []

    # Scan for IKI patterns in the recent portion of data
    scan_start = max(atr_period, len(ohlcv) - 60)
    impulse_threshold = ATR_IMPULSE_MULTIPLIER * atr

    for i in range(scan_start, len(ohlcv) - 10):
        # Look for bullish impulse
        bullish_iki = _find_iki(closes, highs, lows, i, impulse_threshold, bullish=True)
        if bullish_iki:
            results.append(bullish_iki)

        # Look for bearish impulse
        bearish_iki = _find_iki(closes, highs, lows, i, impulse_threshold, bullish=False)
        if bearish_iki:
            results.append(bearish_iki)

    # Deduplicate: keep only the most recent pattern per direction
    seen: dict[bool, PatternDetection] = {}
    for pattern in results:
        seen[pattern.bullish] = pattern

    return list(seen.values())


def _find_iki(
    closes: npt.NDArray[np.float64],
    highs: npt.NDArray[np.float64],
    lows: npt.NDArray[np.float64],
    start: int,
    impulse_threshold: float,
    bullish: bool,
) -> PatternDetection | None:
    """Try to find an IKI pattern starting at index `start`."""
    n = len(closes)
    max_impulse_len = 10
    max_correction_len = 15

    # Phase 1: First impulse
    impulse_end = None
    for j in range(start + 2, min(start + max_impulse_len, n)):
        move = float(highs[j] - lows[start]) if bullish else float(highs[start] - lows[j])

        if move >= impulse_threshold:
            impulse_end = j
            break

    if impulse_end is None:
        return None

    if bullish:
        impulse_start_price = float(lows[start])
        impulse_end_price = float(highs[impulse_end])
    else:
        impulse_start_price = float(highs[start])
        impulse_end_price = float(lows[impulse_end])

    impulse_size = abs(impulse_end_price - impulse_start_price)

    # Phase 2: Correction (38.2% - 61.8% retracement)
    correction_end = None
    correction_price = None

    for k in range(impulse_end + 1, min(impulse_end + max_correction_len, n)):
        retrace = impulse_end_price - float(lows[k]) if bullish else float(highs[k]) - impulse_end_price

        retrace_ratio = retrace / impulse_size if impulse_size > 0 else 0

        if FIBO_RETRACEMENT_MIN <= retrace_ratio <= FIBO_RETRACEMENT_MAX:
            correction_end = k
            correction_price = float(lows[k]) if bullish else float(highs[k])
            break

        # Too deep correction — abort
        if retrace_ratio > FIBO_RETRACEMENT_MAX:
            return None

    if correction_end is None or correction_price is None:
        return None
    remaining = min(correction_end + max_impulse_len, n)
    for m in range(correction_end + 1, remaining):
        second_move = float(highs[m]) - correction_price if bullish else correction_price - float(lows[m])

        if second_move >= impulse_threshold * 0.5:
            confidence = min(1.0, (second_move / impulse_threshold) * 0.7 + 0.3)
            direction = "Bullish" if bullish else "Bearish"
            return PatternDetection(
                pattern_type=f"IKI ({direction})",
                confidence=round(confidence, 2),
                description=(
                    f"{direction} IKI: impulse {impulse_size:.2f}, "
                    f"correction to {correction_price:.2f}, second impulse confirmed"
                ),
                location=f"candle_{start}_{m}",
                bullish=bullish,
                category=PatternCategory.IKI,
                detected_at_index=start,
            )

    return None


def _calculate_atr(
    highs: npt.NDArray[np.float64],
    lows: npt.NDArray[np.float64],
    closes: npt.NDArray[np.float64],
    period: int,
) -> float:
    """Calculate the current ATR (Average True Range) value."""
    n = len(closes)
    if n < period + 1:
        return 0.0

    tr = np.empty(n - 1, dtype=np.float64)
    for i in range(1, n):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr[i - 1] = max(hl, hc, lc)

    # Simple mean of last `period` true ranges
    return float(np.mean(tr[-period:]))

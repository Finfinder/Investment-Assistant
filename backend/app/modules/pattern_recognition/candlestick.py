"""Candlestick pattern detection using TA-Lib."""

import numpy as np
import talib

from app.core.models import OHLCVData, PatternCategory, PatternDetection

# Mapping: ta-lib function name → (human-readable name, description)
CANDLESTICK_PATTERNS: dict[str, tuple[str, str]] = {
    "CDLENGULFING": ("Engulfing", "Bullish/Bearish Engulfing pattern"),
    "CDLHAMMER": ("Hammer", "Hammer — potential bullish reversal"),
    "CDLDOJI": ("Doji", "Doji — market indecision"),
    "CDLSHOOTINGSTAR": ("Shooting Star", "Shooting Star — potential bearish reversal"),
    "CDLMORNINGSTAR": ("Morning Star", "Morning Star — bullish reversal"),
    "CDLEVENINGSTAR": ("Evening Star", "Evening Star — bearish reversal"),
    "CDLHARAMI": ("Harami", "Harami — potential reversal"),
    "CDLPIERCING": ("Piercing", "Piercing Line — bullish reversal"),
    "CDLDARKCLOUDCOVER": ("Dark Cloud Cover", "Dark Cloud Cover — bearish reversal"),
    "CDL3WHITESOLDIERS": ("Three White Soldiers", "Three White Soldiers — strong bullish continuation"),
    "CDL3BLACKCROWS": ("Three Black Crows", "Three Black Crows — strong bearish continuation"),
    "CDLINVERTEDHAMMER": ("Inverted Hammer", "Inverted Hammer — potential bullish reversal"),
    "CDLHANGINGMAN": ("Hanging Man", "Hanging Man — potential bearish reversal"),
    "CDLMARUBOZU": ("Marubozu", "Marubozu — strong momentum candle"),
    "CDLSPINNINGTOP": ("Spinning Top", "Spinning Top — market indecision"),
}


def detect_candlestick_patterns(ohlcv: list[OHLCVData]) -> list[PatternDetection]:
    """Detect candlestick patterns using TA-Lib CDL* functions.

    Returns only patterns detected on the last candle (non-zero result).
    TA-Lib returns -100 (bearish), 0 (none), or +100 (bullish).
    """
    if len(ohlcv) < 5:
        return []

    open_ = np.array([c.open for c in ohlcv], dtype=np.float64)
    high = np.array([c.high for c in ohlcv], dtype=np.float64)
    low = np.array([c.low for c in ohlcv], dtype=np.float64)
    close = np.array([c.close for c in ohlcv], dtype=np.float64)

    results: list[PatternDetection] = []

    for func_name, (pattern_name, description) in CANDLESTICK_PATTERNS.items():
        func = getattr(talib, func_name)
        signal = func(open_, high, low, close)
        last_value = int(signal[-1])

        if last_value == 0:
            continue

        bullish = last_value > 0
        confidence = 1.0 if abs(last_value) == 200 else 0.7

        desc = description
        if func_name == "CDLENGULFING" and not bullish:
            desc = "Objęcie bessy (nóż) — strong bearish reversal signal"

        results.append(
            PatternDetection(
                pattern_type=pattern_name,
                confidence=confidence,
                description=desc,
                location="last_candle",
                bullish=bullish,
                category=PatternCategory.CANDLESTICK,
                detected_at_index=len(ohlcv) - 1,
            )
        )

    return results

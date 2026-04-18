"""Geometric chart pattern detection: wedge, flag, pennant, triangle."""

import numpy as np
import numpy.typing as npt
from scipy.signal import argrelextrema

from app.core.models import OHLCVData, PatternCategory, PatternDetection


def detect_chart_patterns(
    ohlcv: list[OHLCVData],
    lookback: int = 60,
    order: int = 5,
) -> list[PatternDetection]:
    """Detect geometric chart patterns via trendline analysis.

    Identifies:
    - Ascending/Descending/Symmetric Triangle
    - Wedge (rising/falling)
    - Flag (bull/bear)
    - Pennant

    Uses linear regression on peaks and troughs to determine trendline slopes.
    """
    if len(ohlcv) < lookback:
        return []

    data = ohlcv[-lookback:]
    highs = np.array([c.high for c in data], dtype=np.float64)
    lows = np.array([c.low for c in data], dtype=np.float64)
    closes = np.array([c.close for c in data], dtype=np.float64)

    peak_idx = argrelextrema(highs, np.greater_equal, order=order)[0]
    trough_idx = argrelextrema(lows, np.less_equal, order=order)[0]

    if len(peak_idx) < 3 or len(trough_idx) < 3:
        return []

    # Fit trendlines through peaks and troughs
    upper_slope, upper_intercept = _fit_line(peak_idx, highs[peak_idx])
    lower_slope, lower_intercept = _fit_line(trough_idx, lows[trough_idx])

    if upper_slope is None or lower_slope is None:
        return []
    if upper_intercept is None or lower_intercept is None:
        return []

    results: list[PatternDetection] = []

    # Determine convergence / divergence
    mid_x = lookback / 2
    upper_at_mid = upper_slope * mid_x + upper_intercept
    lower_at_mid = lower_slope * mid_x + lower_intercept
    channel_width = upper_at_mid - lower_at_mid if upper_at_mid > lower_at_mid else 1.0

    # Normalize slopes relative to price range
    norm_upper = upper_slope / channel_width * lookback
    norm_lower = lower_slope / channel_width * lookback

    converging = norm_upper < -0.05 or norm_lower > 0.05
    parallel = abs(norm_upper - norm_lower) < 0.15

    # Detect prior impulse (for flag/pennant classification)
    pre_impulse = _has_prior_impulse(closes, lookback)

    pattern = _classify_pattern(norm_upper, norm_lower, converging, parallel, pre_impulse)

    if pattern:
        name, bullish, confidence = pattern
        results.append(
            PatternDetection(
                pattern_type=name,
                confidence=confidence,
                description=f"{name} detected (upper slope: {upper_slope:.4f}, lower slope: {lower_slope:.4f})",
                location=f"last_{lookback}_candles",
                bullish=bullish,
                category=PatternCategory.CHART_PATTERN,
                detected_at_index=len(ohlcv) - lookback,
            )
        )

    return results


def _fit_line(x: npt.NDArray[np.intp], y: npt.NDArray[np.float64]) -> tuple[float | None, float | None]:
    """Fit a linear regression line. Returns (slope, intercept) or (None, None)."""
    if len(x) < 2:
        return None, None

    x_float = x.astype(np.float64)
    coeffs = np.polyfit(x_float, y, 1)
    return float(coeffs[0]), float(coeffs[1])


def _has_prior_impulse(closes: npt.NDArray[np.float64], lookback: int) -> bool:
    """Check if there was a strong impulse move before the pattern window."""
    if len(closes) <= lookback:
        return False

    pre_data = closes[:-lookback]
    if len(pre_data) < 10:
        return False

    last_10 = pre_data[-10:]
    move_pct = abs(float(last_10[-1]) - float(last_10[0])) / float(last_10[0]) * 100
    return bool(move_pct > 3.0)


def _classify_pattern(
    norm_upper: float,
    norm_lower: float,
    converging: bool,
    parallel: bool,
    pre_impulse: bool,
) -> tuple[str, bool, float] | None:
    """Classify the geometric pattern based on trendline characteristics.

    Returns (pattern_name, is_bullish, confidence) or None.
    """
    # Triangles: converging trendlines without prior impulse requirement
    if converging and not parallel:
        if norm_upper < -0.1 and norm_lower > 0.1:
            return "Symmetric Triangle", True, 0.55
        if norm_upper < -0.1 and abs(norm_lower) < 0.1:
            return "Descending Triangle", False, 0.6
        if abs(norm_upper) < 0.1 and norm_lower > 0.1:
            return "Ascending Triangle", True, 0.6

    # Flag / Pennant: require prior impulse
    if pre_impulse:
        if converging:
            return "Pennant", True, 0.6
        if parallel and abs(norm_upper) < 0.3 and abs(norm_lower) < 0.3:
            bullish = norm_upper < 0  # Counter-trend channel = continuation
            name = "Bull Flag" if bullish else "Bear Flag"
            return name, bullish, 0.6

    # Wedge: both trendlines pointing same direction but converging
    if norm_upper > 0.05 and norm_lower > 0.05 and converging:
        return "Rising Wedge", False, 0.55
    if norm_upper < -0.05 and norm_lower < -0.05 and converging:
        return "Falling Wedge", True, 0.55

    return None

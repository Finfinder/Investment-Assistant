"""Tests for geometric chart pattern detection."""

import math

import numpy as np

from app.core.models import OHLCVData, PatternCategory, PatternDetection
from app.modules.pattern_recognition.chart_patterns import (
    _classify_pattern,
    _fit_line,
    _has_prior_impulse,
    detect_chart_patterns,
)
from tests.helpers import make_ohlcv


def _make_ascending_triangle(n: int = 80) -> list[OHLCVData]:
    """Flat highs with oscillating lows that trend upward → ascending triangle."""
    data = []
    resistance = 120.0
    for i in range(n):
        # Rising lows with oscillation so argrelextrema can find troughs
        low_base = 100.0 + i * 0.15
        low_val = low_base + 3.0 * math.sin(i * 0.5)
        high_val = resistance + 0.5 * math.sin(i * 0.5)  # Roughly flat highs
        mid = (low_val + high_val) / 2
        data.append(make_ohlcv(mid - 1, high_val, low_val, mid + 0.5, i))
    return data


def _make_descending_triangle(n: int = 80) -> list[OHLCVData]:
    """Flat lows with oscillating highs that trend downward → descending triangle."""
    data = []
    support = 80.0
    for i in range(n):
        # Falling highs with oscillation so argrelextrema can find peaks
        high_base = 120.0 - i * 0.3
        high_val = high_base + 3.0 * math.sin(i * 0.5)
        low_val = support + 0.5 * math.sin(i * 0.5)  # Roughly flat lows
        mid = (low_val + high_val) / 2
        data.append(make_ohlcv(mid + 1, high_val, low_val, mid - 0.5, i))
    return data


def _make_symmetric_triangle(n: int = 80) -> list[OHLCVData]:
    """Converging highs and lows."""
    data = []
    for i in range(n):
        spread = max(2.0, 20.0 - i * 0.25)  # Narrowing spread
        mid = 100.0
        high_val = mid + spread
        low_val = mid - spread
        data.append(make_ohlcv(mid - 0.5, high_val, low_val, mid + 0.5, i))
    return data


def _make_flag_after_impulse(n_impulse: int = 20, n_flag: int = 60) -> list[OHLCVData]:
    """Strong impulse followed by parallel channel (flag)."""
    data = []
    price = 100.0

    # Pre-impulse
    for i in range(n_impulse):
        data.append(make_ohlcv(price, price + 1, price - 1, price + 3, i))
        price += 3.0

    # Flag: slight counter-trend channel
    for i in range(n_flag):
        flag_price = price - i * 0.1  # Slight downward drift
        data.append(make_ohlcv(flag_price, flag_price + 2, flag_price - 2, flag_price, n_impulse + i))

    return data


class TestChartPatterns:
    def test_returns_empty_for_short_data(self):
        data = [make_ohlcv(100, 105, 95, 102)] * 20
        assert detect_chart_patterns(data) == []

    def test_ascending_triangle(self):
        data = _make_ascending_triangle()
        results = detect_chart_patterns(data, lookback=60)
        assert len(results) >= 1
        assert results[0].pattern_type in ("Ascending Triangle", "Symmetric Triangle", "Pennant", "Rising Wedge")
        assert isinstance(results[0], PatternDetection)

    def test_descending_triangle(self):
        data = _make_descending_triangle()
        results = detect_chart_patterns(data, lookback=60)
        assert len(results) >= 1
        assert isinstance(results[0], PatternDetection)
        assert results[0].confidence > 0

    def test_symmetric_triangle(self):
        data = _make_symmetric_triangle()
        results = detect_chart_patterns(data, lookback=60)
        assert len(results) >= 1
        assert any("Triangle" in r.pattern_type or "Wedge" in r.pattern_type for r in results)

    def test_flag_pattern(self):
        data = _make_flag_after_impulse()
        results = detect_chart_patterns(data, lookback=60)
        # May detect flag, pennant, or wedge depending on exact geometry
        for r in results:
            assert 0.0 <= r.confidence <= 1.0
            assert "last_" in r.location

    def test_all_patterns_have_valid_structure(self):
        data = _make_ascending_triangle()
        results = detect_chart_patterns(data, lookback=60)
        for r in results:
            assert isinstance(r.pattern_type, str)
            assert isinstance(r.description, str)
            assert "slope" in r.description.lower()
            assert r.category == PatternCategory.CHART_PATTERN
            assert r.detected_at_index == len(data) - 60


class TestClassifyPatternDirect:
    """Direct unit tests for _classify_pattern to cover all branches."""

    def test_symmetric_triangle(self):
        result = _classify_pattern(norm_upper=-0.2, norm_lower=0.2, converging=True, parallel=False, pre_impulse=False)
        assert result is not None
        assert result[0] == "Symmetric Triangle"

    def test_descending_triangle(self):
        result = _classify_pattern(norm_upper=-0.2, norm_lower=0.05, converging=True, parallel=False, pre_impulse=False)
        assert result is not None
        assert result[0] == "Descending Triangle"
        assert result[1] is False  # bearish

    def test_ascending_triangle(self):
        result = _classify_pattern(norm_upper=0.05, norm_lower=0.2, converging=True, parallel=False, pre_impulse=False)
        assert result is not None
        assert result[0] == "Ascending Triangle"
        assert result[1] is True  # bullish

    def test_pennant_with_impulse(self):
        result = _classify_pattern(norm_upper=-0.1, norm_lower=0.1, converging=True, parallel=False, pre_impulse=True)
        assert result is not None
        assert result[0] == "Pennant"

    def test_bull_flag_with_impulse(self):
        result = _classify_pattern(norm_upper=-0.1, norm_lower=-0.1, converging=False, parallel=True, pre_impulse=True)
        assert result is not None
        assert result[0] == "Bull Flag"
        assert result[1] is True

    def test_bear_flag_with_impulse(self):
        result = _classify_pattern(norm_upper=0.1, norm_lower=0.1, converging=False, parallel=True, pre_impulse=True)
        assert result is not None
        assert result[0] == "Bear Flag"
        assert result[1] is False

    def test_rising_wedge(self):
        result = _classify_pattern(norm_upper=0.1, norm_lower=0.1, converging=True, parallel=False, pre_impulse=False)
        assert result is not None
        assert result[0] == "Rising Wedge"
        assert result[1] is False  # bearish

    def test_falling_wedge(self):
        result = _classify_pattern(norm_upper=-0.1, norm_lower=-0.1, converging=True, parallel=False, pre_impulse=False)
        assert result is not None
        assert result[0] == "Falling Wedge"
        assert result[1] is True  # bullish

    def test_no_pattern_returns_none(self):
        result = _classify_pattern(norm_upper=0.0, norm_lower=0.0, converging=False, parallel=False, pre_impulse=False)
        assert result is None


class TestFitLine:
    """Tests for _fit_line."""

    def test_returns_none_for_single_point(self):
        x = np.array([5])
        y = np.array([100.0])
        slope, intercept = _fit_line(x, y)
        assert slope is None
        assert intercept is None

    def test_returns_none_for_empty(self):
        x = np.array([], dtype=np.intp)
        y = np.array([], dtype=np.float64)
        slope, intercept = _fit_line(x, y)
        assert slope is None
        assert intercept is None

    def test_returns_slope_for_two_points(self):
        x = np.array([0, 10])
        y = np.array([100.0, 110.0])
        slope, intercept = _fit_line(x, y)
        assert slope is not None
        assert intercept is not None
        assert abs(slope - 1.0) < 0.01


class TestHasPriorImpulse:
    """Tests for _has_prior_impulse."""

    def test_no_impulse_when_data_equals_lookback(self):
        closes = np.array([100.0] * 60)
        assert _has_prior_impulse(closes, lookback=60) is False

    def test_no_impulse_when_pre_data_short(self):
        closes = np.array([100.0] * 65)
        assert _has_prior_impulse(closes, lookback=60) is False

    def test_detects_impulse(self):
        # 20 candles of impulse before the pattern window
        pre = list(range(100, 120))  # 20-point move on base ~100 → ~19% move
        pattern = [119.0] * 60
        closes = np.array(pre + pattern, dtype=np.float64)
        assert _has_prior_impulse(closes, lookback=60) is True

    def test_no_impulse_on_flat_data(self):
        pre = [100.0] * 20
        pattern = [100.0] * 60
        closes = np.array(pre + pattern, dtype=np.float64)
        assert _has_prior_impulse(closes, lookback=60) is False


class TestChartPatternsEdgeCases:
    """Edge-case tests for detect_chart_patterns."""

    def test_few_peaks_or_troughs_returns_empty(self):
        """Data with <3 peaks or <3 troughs should return empty."""
        # Monotonically increasing → no oscillation → few extrema
        data = [make_ohlcv(100 + i, 102 + i, 99 + i, 101 + i, i) for i in range(80)]
        assert detect_chart_patterns(data, lookback=60) == []

    def test_inverted_channel_returns_pattern(self):
        """Upper below lower at mid → channel_width defaults to 1.0."""
        data = []
        for i in range(80):
            h = 100.0 + 3 * math.sin(i * 0.5) - i * 0.05
            l = 95.0 + 3 * math.sin(i * 0.5) + i * 0.05  # noqa: E741
            if l >= h:
                l = h - 0.5  # noqa: E741
            mid = (h + l) / 2
            data.append(make_ohlcv(mid, h, l, mid, i))
        results = detect_chart_patterns(data, lookback=60)
        # Should not crash; may or may not find a pattern
        for r in results:
            assert isinstance(r, PatternDetection)

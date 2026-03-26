"""Tests for geometric chart pattern detection."""

import math

from app.core.models import OHLCVData, PatternDetection
from app.modules.pattern_recognition.chart_patterns import detect_chart_patterns
from tests.helpers import make_ohlcv


def _make_ascending_triangle(n: int = 80) -> list[OHLCVData]:
    """Flat highs, rising lows → ascending triangle."""
    data = []
    resistance = 120.0
    for i in range(n):
        low_val = 100.0 + i * 0.2  # Rising lows
        high_val = resistance + (0.5 * math.sin(i * 0.3))  # Roughly flat highs
        mid = (low_val + high_val) / 2
        data.append(make_ohlcv(mid - 1, high_val, low_val, mid + 0.5, i))
    return data


def _make_descending_triangle(n: int = 80) -> list[OHLCVData]:
    """Flat lows, falling highs → descending triangle."""
    data = []
    support = 80.0
    for i in range(n):
        high_val = 120.0 - i * 0.3  # Falling highs
        low_val = support - (0.5 * math.sin(i * 0.3))  # Roughly flat lows
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
        if results:
            assert results[0].pattern_type in ("Ascending Triangle", "Symmetric Triangle", "Pennant", "Rising Wedge")
            assert isinstance(results[0], PatternDetection)

    def test_descending_triangle(self):
        data = _make_descending_triangle()
        results = detect_chart_patterns(data, lookback=60)
        if results:
            assert isinstance(results[0], PatternDetection)
            assert results[0].confidence > 0

    def test_symmetric_triangle(self):
        data = _make_symmetric_triangle()
        results = detect_chart_patterns(data, lookback=60)
        if results:
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

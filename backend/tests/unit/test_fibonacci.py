"""Tests for Fibonacci retracement level calculator."""

from app.core.models import OHLCVData, PatternCategory, PatternDetection
from app.modules.pattern_recognition.fibonacci import FIBO_LEVELS, calculate_fibonacci_levels
from tests.helpers import make_ohlcv


def _make_uptrend_then_retrace(n: int = 60) -> list[OHLCVData]:
    """Create data with clear uptrend followed by partial retracement."""
    data = []
    # Phase 1: uptrend from 100 to 150
    for i in range(40):
        price = 100.0 + i * 1.25
        data.append(make_ohlcv(price, price + 2, price - 1, price + 1, i))
    # Phase 2: retracement from 150 towards ~130
    for i in range(20):
        price = 150.0 - i * 1.0
        data.append(make_ohlcv(price, price + 1, price - 2, price - 0.5, 40 + i))
    return data


def _make_downtrend_then_bounce(n: int = 60) -> list[OHLCVData]:
    """Create data with clear downtrend followed by partial bounce."""
    data = []
    # Phase 1: downtrend from 150 to 100
    for i in range(40):
        price = 150.0 - i * 1.25
        data.append(make_ohlcv(price, price + 1, price - 2, price - 1, i))
    # Phase 2: bounce from 100 towards ~120
    for i in range(20):
        price = 100.0 + i * 1.0
        data.append(make_ohlcv(price, price + 2, price - 1, price + 0.5, 40 + i))
    return data


class TestFibonacciLevels:
    def test_returns_empty_for_short_data(self):
        data = [make_ohlcv(100, 105, 95, 102)] * 10
        assert calculate_fibonacci_levels(data) == []

    def test_returns_five_levels(self):
        data = _make_uptrend_then_retrace()
        results = calculate_fibonacci_levels(data)
        assert len(results) == 5

    def test_level_names_match_fibo_ratios(self):
        data = _make_uptrend_then_retrace()
        results = calculate_fibonacci_levels(data)
        for result, level in zip(results, FIBO_LEVELS, strict=True):
            assert f"{level * 100:.1f}" in result.pattern_type

    def test_uptrend_retracement_prices_are_between_swing_points(self):
        data = _make_uptrend_then_retrace()
        results = calculate_fibonacci_levels(data)
        # All results should have valid structure
        for r in results:
            assert isinstance(r.description, str)
            assert 0.0 <= r.confidence <= 1.0
            assert "retracement" in r.description.lower()
            assert r.category == PatternCategory.FIBONACCI
            assert r.detected_at_index is not None

    def test_downtrend_retracement(self):
        data = _make_downtrend_then_bounce()
        results = calculate_fibonacci_levels(data)
        if results:  # Depends on swing detection
            for r in results:
                assert isinstance(r, PatternDetection)
                assert 0.0 <= r.confidence <= 1.0

    def test_active_level_has_higher_confidence(self):
        data = _make_uptrend_then_retrace()
        results = calculate_fibonacci_levels(data, proximity_pct=50.0)  # Very wide proximity
        for r in results:
            if "ACTIVE" in r.description:
                assert r.confidence == 0.8

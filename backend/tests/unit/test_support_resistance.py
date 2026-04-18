"""Tests for support and resistance detection."""

import math

from app.core.models import OHLCVData, PatternCategory, PatternDetection
from app.modules.pattern_recognition.support_resistance import detect_support_resistance
from tests.helpers import make_ohlcv


def _make_oscillating_data(n: int = 100, base: float = 100.0, amplitude: float = 10.0) -> list[OHLCVData]:
    """Create oscillating data with clear peaks and valleys."""
    data = []
    for i in range(n):
        mid = base + amplitude * math.sin(i * 0.2)
        o = mid - 0.5
        c = mid + 0.5
        h = mid + 2.0
        lo = mid - 2.0
        data.append(make_ohlcv(o, h, lo, c, i))
    return data


class TestSupportResistance:
    def test_returns_empty_for_short_data(self):
        data = [make_ohlcv(100, 105, 95, 102)] * 5
        assert detect_support_resistance(data) == []

    def test_detects_levels_on_oscillating_data(self):
        data = _make_oscillating_data(120)
        results = detect_support_resistance(data)
        assert len(results) > 0
        for r in results:
            assert isinstance(r, PatternDetection)
            assert "S/R Level" in r.pattern_type or "EMA" in r.pattern_type
            assert r.category == PatternCategory.SUPPORT_RESISTANCE
            assert r.detected_at_index == len(data) - 1

    def test_levels_have_correct_types(self):
        data = _make_oscillating_data(120)
        results = detect_support_resistance(data)
        sr_levels = [r for r in results if "S/R Level" in r.pattern_type]
        for level in sr_levels:
            assert "support" in level.pattern_type.lower() or "resistance" in level.pattern_type.lower()
            assert 0.0 <= level.confidence <= 1.0
            assert "touches" in level.description

    def test_ema_bounce_detection(self):
        # Create data where price ends close to EMA 50
        data = []
        for i in range(100):
            price = 100.0 + i * 0.01  # Very slow trend
            data.append(make_ohlcv(price, price + 0.5, price - 0.5, price, i))

        results = detect_support_resistance(data)
        ema_patterns = [r for r in results if "EMA" in r.pattern_type]
        # EMA should be close to price in a slow trend
        for ep in ema_patterns:
            assert ep.confidence > 0.0

    def test_cluster_tolerance(self):
        data = _make_oscillating_data(120, amplitude=5.0)
        results_tight = detect_support_resistance(data, cluster_tolerance_pct=0.1)
        results_wide = detect_support_resistance(data, cluster_tolerance_pct=2.0)
        # Wider tolerance should cluster more levels together → fewer results
        sr_tight = [r for r in results_tight if "S/R" in r.pattern_type]
        sr_wide = [r for r in results_wide if "S/R" in r.pattern_type]
        assert len(sr_wide) <= len(sr_tight)

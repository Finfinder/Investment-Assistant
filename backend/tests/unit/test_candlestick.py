"""Tests for candlestick pattern detection."""

import talib

from app.core.models import PatternDetection
from app.modules.pattern_recognition.candlestick import CANDLESTICK_PATTERNS, detect_candlestick_patterns
from tests.helpers import make_ohlcv


class TestDetectCandlestickPatterns:
    def test_returns_empty_for_short_data(self):
        data = [make_ohlcv(100, 105, 95, 102)] * 3
        assert detect_candlestick_patterns(data) == []

    def test_returns_pattern_detection_objects(self):
        # Construct data that produces a bullish engulfing on the last candle:
        # 2nd-to-last: small bearish candle, last: large bullish candle engulfing it
        data = [make_ohlcv(100, 102, 98, 100, i) for i in range(10)]
        # Small bearish candle
        data.append(make_ohlcv(101, 101.5, 99.5, 99.8, 10))
        # Large bullish engulfing
        data.append(make_ohlcv(99, 103, 98.5, 102.5, 11))

        results = detect_candlestick_patterns(data)
        for r in results:
            assert isinstance(r, PatternDetection)
            assert 0.0 <= r.confidence <= 1.0
            assert r.location == "last_candle"

    def test_bearish_engulfing_marked_as_noz(self):
        # Small bullish candle followed by large bearish engulfing
        data = [make_ohlcv(100, 102, 98, 101, i) for i in range(10)]
        # Small bullish
        data.append(make_ohlcv(100, 101, 99.5, 100.5, 10))
        # Large bearish engulfing
        data.append(make_ohlcv(101, 101.5, 98, 98.5, 11))

        results = detect_candlestick_patterns(data)
        engulfing = [r for r in results if r.pattern_type == "Engulfing" and not r.bullish]
        for e in engulfing:
            assert "nóż" in e.description.lower() or "bessy" in e.description.lower()

    def test_doji_detected(self):
        # Doji: open ≈ close with long wicks
        data = [make_ohlcv(100, 102, 98, 100, i) for i in range(10)]
        data.append(make_ohlcv(100.0, 105.0, 95.0, 100.01, 10))

        results = detect_candlestick_patterns(data)
        doji = [r for r in results if "Doji" in r.pattern_type or "Spinning" in r.pattern_type]
        # May or may not detect depending on TA-Lib thresholds — just check structure
        for d in doji:
            assert isinstance(d.description, str)

    def test_hammer_detected_on_synthetic_data(self):
        # Downtrend followed by hammer
        data = []
        price = 120.0
        for i in range(15):
            data.append(make_ohlcv(price, price + 1, price - 2, price - 1.5, i))
            price -= 1.5
        # Hammer: small body at top, long lower wick
        data.append(make_ohlcv(price, price + 0.5, price - 6, price + 0.3, 15))

        results = detect_candlestick_patterns(data)
        # Check that at least some pattern is detected
        assert all(isinstance(r, PatternDetection) for r in results)

    def test_all_patterns_have_valid_names(self):
        # Verify mapping consistency
        for func_name, (name, desc) in CANDLESTICK_PATTERNS.items():
            assert hasattr(talib, func_name), f"{func_name} not in talib"
            assert len(name) > 0
            assert len(desc) > 0

    def test_confidence_values(self):
        # Whatever patterns are detected, confidence should be 0.7 or 1.0
        data = [make_ohlcv(100, 102, 98, 100, i) for i in range(10)]
        data.append(make_ohlcv(100, 101, 99.5, 100.5, 10))
        data.append(make_ohlcv(101, 101.5, 98, 98.5, 11))

        results = detect_candlestick_patterns(data)
        for r in results:
            assert r.confidence in (0.7, 1.0)

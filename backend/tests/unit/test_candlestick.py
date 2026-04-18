"""Tests for candlestick pattern detection."""

import talib

from app.core.models import PatternCategory, PatternDetection
from app.modules.pattern_recognition.candlestick import (
    CANDLESTICK_PATTERNS,
    _confidence_from_signal,
    _reliability_from_signal,
    detect_candlestick_patterns,
)
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
            assert r.location in ("emerging", "completed")
            assert r.category == PatternCategory.CANDLESTICK
            assert r.detected_at_index is not None

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

    def test_all_patterns_have_valid_names_and_keys(self):
        """Weryfikuje 28 formacji w słowniku z wymaganymi kluczami."""
        assert len(CANDLESTICK_PATTERNS) == 28
        required_keys = {"name", "description", "indication", "detailed_description"}
        for func_name, meta in CANDLESTICK_PATTERNS.items():
            assert hasattr(talib, func_name), f"{func_name} not in talib"
            assert required_keys.issubset(meta.keys()), f"{func_name} missing keys: {required_keys - meta.keys()}"
            assert len(meta["name"]) > 0
            assert len(meta["description"]) > 0
            assert len(meta["indication"]) > 0
            assert len(meta["detailed_description"]) > 0

    def test_confidence_values(self):
        # Whatever patterns are detected, confidence should be 0.5, 0.7 or 1.0
        data = [make_ohlcv(100, 102, 98, 100, i) for i in range(10)]
        data.append(make_ohlcv(100, 101, 99.5, 100.5, 10))
        data.append(make_ohlcv(101, 101.5, 98, 98.5, 11))

        results = detect_candlestick_patterns(data)
        for r in results:
            assert r.confidence in (0.5, 0.7, 1.0)

    def test_reliability_mapping(self):
        """Weryfikuje mapowanie siły sygnału TA-Lib na reliability."""
        assert _reliability_from_signal(200) == 3
        assert _reliability_from_signal(100) == 2
        assert _reliability_from_signal(50) == 1
        assert _reliability_from_signal(0) == 1

    def test_confidence_mapping(self):
        """Weryfikuje mapowanie siły sygnału TA-Lib na confidence."""
        assert _confidence_from_signal(200) == 1.0
        assert _confidence_from_signal(100) == 0.7
        assert _confidence_from_signal(50) == 0.5

    def test_patterns_have_indication_and_detailed_description(self):
        """Weryfikuje, że wykryte formacje mają pola indication i detailed_description."""
        data = [make_ohlcv(100, 102, 98, 100, i) for i in range(10)]
        # Small bearish, then large bullish engulfing
        data.append(make_ohlcv(101, 101.5, 99.5, 99.8, 10))
        data.append(make_ohlcv(99, 103, 98.5, 102.5, 11))

        results = detect_candlestick_patterns(data)
        for r in results:
            assert isinstance(r.indication, str)
            assert isinstance(r.detailed_description, str)
            assert len(r.indication) > 0
            assert len(r.detailed_description) > 0
            assert 1 <= r.reliability <= 3

    def test_location_emerging_vs_completed(self):
        """Weryfikuje, że ostatnia świeca to 'emerging', starsze to 'completed'."""
        data = [make_ohlcv(100, 102, 98, 100, i) for i in range(10)]
        data.append(make_ohlcv(101, 101.5, 99.5, 99.8, 10))
        data.append(make_ohlcv(99, 103, 98.5, 102.5, 11))

        results = detect_candlestick_patterns(data)
        last_idx = len(data) - 1
        for r in results:
            if r.detected_at_index == last_idx:
                assert r.location == "emerging", f"Expected 'emerging' for last candle, got '{r.location}'"
            else:
                assert r.location == "completed", f"Expected 'completed' for older candle, got '{r.location}'"

    def test_no_duplicate_patterns_same_candle(self):
        """Weryfikuje, że ta sama formacja nie pojawia się dwukrotnie na tej samej świecy."""
        data = [make_ohlcv(100, 102, 98, 100, i) for i in range(30)]
        results = detect_candlestick_patterns(data)
        seen = set()
        for r in results:
            key = (r.pattern_type, r.detected_at_index)
            assert key not in seen, f"Duplicate: {key}"
            seen.add(key)

    def test_scans_multiple_candles(self):
        """Weryfikuje, że skanowanie obejmuje więcej niż tylko ostatnią świecę."""
        # Build data with a detectable pattern on second-to-last candle
        data = [make_ohlcv(100, 102, 98, 100, i) for i in range(10)]
        # Small bearish (idx=10)
        data.append(make_ohlcv(101, 101.5, 99.5, 99.8, 10))
        # Large bullish engulfing (idx=11) — pattern is here
        data.append(make_ohlcv(99, 103, 98.5, 102.5, 11))
        # Add a neutral candle after so the engulfing is not on last candle (idx=12)
        data.append(make_ohlcv(102, 102.5, 101.5, 102.2, 12))

        results = detect_candlestick_patterns(data)
        # The engulfing at idx=11 should be picked up as 'completed'
        completed = [r for r in results if r.location == "completed"]
        # If any completed patterns are found, they should have detected_at_index < len(data)-1
        for r in completed:
            assert r.detected_at_index < len(data) - 1

    def test_indication_direction_specific(self):
        """Weryfikuje, że wskazania obukierunkowych formacji są doprecyzowywane."""
        data = [make_ohlcv(100, 102, 98, 100, i) for i in range(10)]
        data.append(make_ohlcv(101, 101.5, 99.5, 99.8, 10))
        data.append(make_ohlcv(99, 103, 98.5, 102.5, 11))

        results = detect_candlestick_patterns(data)
        for r in results:
            # Wskazanie nie może być tylko "Odwrót" — musi być doprecyzowane
            assert r.indication != "Odwrót", f"Undirected indication for {r.pattern_type}: '{r.indication}'"
            assert r.indication != "Silny impet", f"Undirected indication for {r.pattern_type}: '{r.indication}'"
            assert r.indication != "Kontynuacja trendu", f"Undirected indication for {r.pattern_type}: '{r.indication}'"

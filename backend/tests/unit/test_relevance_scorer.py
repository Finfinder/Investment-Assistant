"""Tests for relevance_scorer — score_patterns() and calculate_target_prices()."""

from app.core.models import PatternCategory, PatternDetection
from app.modules.pattern_recognition.relevance_scorer import (
    calculate_target_prices,
    score_patterns,
)
from tests.helpers import make_ohlcv


def _make_pattern(
    category: PatternCategory = PatternCategory.CANDLESTICK,
    confidence: float = 0.8,
    bullish: bool = True,
    detected_at_index: int | None = None,
    location: str = "last_candle",
    description: str = "",
) -> PatternDetection:
    return PatternDetection(
        pattern_type="Test",
        confidence=confidence,
        description=description,
        location=location,
        bullish=bullish,
        category=category,
        detected_at_index=detected_at_index,
    )


def _make_ohlcv_series(n: int = 100, base: float = 100.0) -> list:
    return [make_ohlcv(base, base + 2, base - 2, base, i) for i in range(n)]


class TestScorePatterns:
    def test_empty_list_no_error(self):
        score_patterns([], total_candles=100)  # No exception

    def test_zero_total_candles_no_error(self):
        p = _make_pattern()
        score_patterns([p], total_candles=0)
        assert p.relevance_score == 0.0  # Unchanged default

    def test_recent_pattern_higher_score_than_old(self):
        total = 100
        recent = _make_pattern(confidence=0.8, detected_at_index=total - 1)
        old = _make_pattern(confidence=0.8, detected_at_index=0)
        score_patterns([recent, old], total_candles=total)
        assert recent.relevance_score > old.relevance_score

    def test_high_confidence_gives_higher_score(self):
        total = 100
        high_conf = _make_pattern(confidence=1.0, detected_at_index=total - 1)
        low_conf = _make_pattern(confidence=0.3, detected_at_index=total - 1)
        score_patterns([high_conf, low_conf], total_candles=total)
        assert high_conf.relevance_score > low_conf.relevance_score

    def test_score_in_valid_range(self):
        total = 100
        patterns = [
            _make_pattern(confidence=1.0, detected_at_index=99),
            _make_pattern(confidence=0.5, detected_at_index=50),
            _make_pattern(confidence=0.1, detected_at_index=0),
        ]
        score_patterns(patterns, total_candles=total)
        for p in patterns:
            assert 0.0 <= p.relevance_score <= 1.0

    def test_none_detected_at_index_uses_fallback(self):
        total = 100
        p = _make_pattern(confidence=0.8, detected_at_index=None)
        score_patterns([p], total_candles=total)
        # Fallback = last candle (index = total - 1) → recency = 1.0
        assert p.relevance_score > 0.0

    def test_last_candle_gets_max_recency(self):
        total = 100
        p = _make_pattern(confidence=0.8, detected_at_index=total - 1)
        score_patterns([p], total_candles=total)
        # recency = 1 - 0/100 = 1.0
        expected = round(0.5 * 0.8 + 0.35 * 1.0 + 0.15 * 1.0, 4)
        assert abs(p.relevance_score - expected) < 0.001


class TestCalculateTargetPrices:
    def test_empty_list_no_error(self):
        calculate_target_prices([], ohlcv=[])

    def test_empty_ohlcv_no_error(self):
        p = _make_pattern()
        calculate_target_prices([p], ohlcv=[])
        assert p.target_price is None

    def test_candlestick_bullish_target_above_current(self):
        ohlcv = _make_ohlcv_series(50, base=100.0)
        p = _make_pattern(category=PatternCategory.CANDLESTICK, bullish=True)
        calculate_target_prices([p], ohlcv=ohlcv)
        assert p.target_price is not None
        assert p.target_price > 100.0

    def test_candlestick_bearish_target_below_current(self):
        ohlcv = _make_ohlcv_series(50, base=100.0)
        p = _make_pattern(category=PatternCategory.CANDLESTICK, bullish=False)
        calculate_target_prices([p], ohlcv=ohlcv)
        assert p.target_price is not None
        assert p.target_price < 100.0

    def test_chart_pattern_bullish_target_above_current(self):
        ohlcv = _make_ohlcv_series(50, base=100.0)
        p = _make_pattern(category=PatternCategory.CHART_PATTERN, bullish=True)
        calculate_target_prices([p], ohlcv=ohlcv)
        assert p.target_price is not None
        assert p.target_price > 100.0

    def test_fibonacci_uses_level_price_from_description(self):
        ohlcv = _make_ohlcv_series(50, base=100.0)
        desc = "Uptrend retracement 38.2% at 95.1234"
        p = _make_pattern(category=PatternCategory.FIBONACCI, description=desc)
        calculate_target_prices([p], ohlcv=ohlcv)
        assert p.target_price is not None
        assert abs(p.target_price - 95.1234) < 0.0001

    def test_fibonacci_no_price_in_description_returns_none(self):
        ohlcv = _make_ohlcv_series(50, base=100.0)
        p = _make_pattern(category=PatternCategory.FIBONACCI, description="no price here")
        calculate_target_prices([p], ohlcv=ohlcv)
        assert p.target_price is None

    def test_sr_uses_price_from_location(self):
        ohlcv = _make_ohlcv_series(50, base=100.0)
        p = _make_pattern(category=PatternCategory.SUPPORT_RESISTANCE, location="price_98.75")
        calculate_target_prices([p], ohlcv=ohlcv)
        assert p.target_price is not None
        assert abs(p.target_price - 98.75) < 0.0001

    def test_sr_ema_location_returns_none(self):
        ohlcv = _make_ohlcv_series(50, base=100.0)
        p = _make_pattern(category=PatternCategory.SUPPORT_RESISTANCE, location="ema_50")
        calculate_target_prices([p], ohlcv=ohlcv)
        assert p.target_price is None

    def test_iki_bullish_target_above_current(self):
        ohlcv = _make_ohlcv_series(50, base=100.0)
        p = _make_pattern(category=PatternCategory.IKI, bullish=True)
        calculate_target_prices([p], ohlcv=ohlcv)
        assert p.target_price is not None
        assert p.target_price > 100.0

    def test_iki_bearish_target_below_current(self):
        ohlcv = _make_ohlcv_series(50, base=100.0)
        p = _make_pattern(category=PatternCategory.IKI, bullish=False)
        calculate_target_prices([p], ohlcv=ohlcv)
        assert p.target_price is not None
        assert p.target_price < 100.0

    def test_short_ohlcv_candlestick_atr_zero_returns_none(self):
        # ATR requires at least 15 candles (period+1); with < 15, atr=0 → target=None
        ohlcv = _make_ohlcv_series(5, base=100.0)
        p = _make_pattern(category=PatternCategory.CANDLESTICK, bullish=True)
        calculate_target_prices([p], ohlcv=ohlcv)
        assert p.target_price is None


class TestSortByRelevance:
    def test_sorted_descending_after_scoring(self):
        total = 100
        patterns = [
            _make_pattern(confidence=0.3, detected_at_index=10),
            _make_pattern(confidence=1.0, detected_at_index=99),
            _make_pattern(confidence=0.7, detected_at_index=80),
        ]
        score_patterns(patterns, total_candles=total)
        patterns.sort(key=lambda p: p.relevance_score, reverse=True)
        scores = [p.relevance_score for p in patterns]
        assert scores == sorted(scores, reverse=True)
        # Highest confidence + most recent should be first
        assert patterns[0].confidence == 1.0


class TestProximity:
    def test_sr_near_current_price_has_higher_proximity(self):
        total = 100
        near = _make_pattern(
            category=PatternCategory.SUPPORT_RESISTANCE,
            confidence=0.8,
            detected_at_index=99,
            location="price_100.50",
        )
        far = _make_pattern(
            category=PatternCategory.SUPPORT_RESISTANCE,
            confidence=0.8,
            detected_at_index=99,
            location="price_120.00",
        )
        score_patterns([near, far], total_candles=total, current_price=100.0)
        assert near.relevance_score > far.relevance_score

    def test_fibonacci_near_current_price_has_higher_proximity(self):
        total = 100
        near = _make_pattern(
            category=PatternCategory.FIBONACCI,
            confidence=0.8,
            detected_at_index=99,
            description="Retracement at 99.50",
        )
        far = _make_pattern(
            category=PatternCategory.FIBONACCI,
            confidence=0.8,
            detected_at_index=99,
            description="Retracement at 80.00",
        )
        score_patterns([near, far], total_candles=total, current_price=100.0)
        assert near.relevance_score > far.relevance_score

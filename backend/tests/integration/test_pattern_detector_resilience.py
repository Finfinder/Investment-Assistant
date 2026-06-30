"""Tests for graceful degradation when pattern detectors raise exceptions."""

from unittest.mock import AsyncMock, patch

from app.core.models import OHLCVData, PatternCategory, PatternDetection
from tests.helpers import make_ohlcv


def _mock_ohlcv(n: int = 100) -> list[OHLCVData]:
    """Generate enough OHLCV data for all detectors."""
    data = []
    price = 100.0
    for i in range(n):
        data.append(make_ohlcv(price, price + 2, price - 2, price + 0.5, i))
        price += 0.5
    return data


class TestPatternDetectorResilience:
    """Verify that a single detector failure does not crash the endpoint."""

    async def test_single_detector_failure_returns_partial_results(self, client):
        """When one detector raises, endpoint returns 200 with partial results and warnings."""
        mock_chain = AsyncMock()
        mock_chain.fetch_ohlcv.return_value = _mock_ohlcv(120)

        with (
            patch("app.api.v1.patterns.get_fallback_chain", return_value=mock_chain),
            patch("app.api.v1.patterns.detect_candlestick_patterns", side_effect=RuntimeError("TA-Lib crash")),
        ):
            resp = await client.post(
                "/api/v1/patterns",
                json={"symbol": "AAPL", "timeframe": "H1"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "AAPL"
        assert isinstance(data["patterns"], list)
        assert "warnings" in data
        assert len(data["warnings"]) == 1
        assert "candlestick" in data["warnings"][0]

    async def test_all_detectors_failure_returns_empty_patterns_with_warnings(self, client):
        """When all detectors fail, endpoint returns 200 with empty patterns and 5 warnings."""
        mock_chain = AsyncMock()
        mock_chain.fetch_ohlcv.return_value = _mock_ohlcv(120)

        with (
            patch("app.api.v1.patterns.get_fallback_chain", return_value=mock_chain),
            patch("app.api.v1.patterns.detect_candlestick_patterns", side_effect=RuntimeError("fail")),
            patch("app.api.v1.patterns.detect_support_resistance", side_effect=RuntimeError("fail")),
            patch("app.api.v1.patterns.calculate_fibonacci_levels", side_effect=RuntimeError("fail")),
            patch("app.api.v1.patterns.detect_iki_pattern", side_effect=RuntimeError("fail")),
            patch("app.api.v1.patterns.detect_chart_patterns", side_effect=RuntimeError("fail")),
        ):
            resp = await client.post(
                "/api/v1/patterns",
                json={"symbol": "AAPL", "timeframe": "H1"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["patterns"] == []
        assert len(data["warnings"]) == 5

    async def test_warning_format_includes_detector_name_and_exception_type(self, client):
        """Warning format is '<detector_name>: <ExceptionType>'."""
        mock_chain = AsyncMock()
        mock_chain.fetch_ohlcv.return_value = _mock_ohlcv(120)

        with (
            patch("app.api.v1.patterns.get_fallback_chain", return_value=mock_chain),
            patch("app.api.v1.patterns.calculate_fibonacci_levels", side_effect=ValueError("NaN encountered")),
        ):
            resp = await client.post(
                "/api/v1/patterns",
                json={"symbol": "AAPL", "timeframe": "H1"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert any("fibonacci" in w and "ValueError" in w for w in data["warnings"])

    async def test_detector_failure_isolation(self, client):
        """A failing detector does not affect results from other detectors."""
        mock_chain = AsyncMock()
        mock_chain.fetch_ohlcv.return_value = _mock_ohlcv(120)

        sentinel = PatternDetection(
            pattern_type="sentinel_support",
            category=PatternCategory.SUPPORT_RESISTANCE,
            confidence=0.9,
            description="Sentinel pattern to verify detector isolation",
        )

        # Make candlestick fail, support_resistance returns sentinel
        with (
            patch("app.api.v1.patterns.get_fallback_chain", return_value=mock_chain),
            patch("app.api.v1.patterns.detect_candlestick_patterns", side_effect=Exception("boom")),
            patch("app.api.v1.patterns.detect_support_resistance", return_value=[sentinel]),
        ):
            resp = await client.post(
                "/api/v1/patterns",
                json={"symbol": "AAPL", "timeframe": "H1"},
            )

        assert resp.status_code == 200
        data = resp.json()
        # Verify the sentinel pattern from working detector is present
        assert any(p["pattern_type"] == "sentinel_support" for p in data["patterns"])
        # And warning for the failed detector
        assert any("candlestick" in w for w in data["warnings"])

    async def test_no_failures_returns_empty_warnings(self, client):
        """When all detectors succeed, warnings is an empty list."""
        mock_chain = AsyncMock()
        mock_chain.fetch_ohlcv.return_value = _mock_ohlcv(120)

        with patch("app.api.v1.patterns.get_fallback_chain", return_value=mock_chain):
            resp = await client.post(
                "/api/v1/patterns",
                json={"symbol": "AAPL", "timeframe": "H1"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["warnings"] == []

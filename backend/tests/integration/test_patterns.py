"""Tests for patterns REST API endpoint."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.models import OHLCVData
from tests.helpers import make_ohlcv


def _mock_ohlcv(n: int = 100) -> list[OHLCVData]:
    """Generate enough OHLCV data for all detectors."""
    data = []
    price = 100.0
    for i in range(n):
        data.append(make_ohlcv(price, price + 2, price - 2, price + 0.5, i))
        price += 0.5
    return data


class TestPatternsEndpoint:
    @pytest.mark.asyncio
    async def test_success(self, client):
        mock_chain = AsyncMock()
        mock_chain.fetch_ohlcv.return_value = _mock_ohlcv(120)

        with patch("app.api.v1.patterns.get_fallback_chain", return_value=mock_chain):
            resp = await client.post(
                "/api/v1/patterns",
                json={"symbol": "AAPL", "timeframe": "H1"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "AAPL"
        assert data["timeframe"] == "H1"
        assert isinstance(data["patterns"], list)
        assert "warnings" in data
        assert isinstance(data["warnings"], list)

    @pytest.mark.asyncio
    async def test_invalid_symbol(self, client):
        resp = await client.post(
            "/api/v1/patterns",
            json={"symbol": "INVALID!!!", "timeframe": "H1"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_no_data_returns_404(self, client):
        mock_chain = AsyncMock()
        mock_chain.fetch_ohlcv.return_value = []

        with patch("app.api.v1.patterns.get_fallback_chain", return_value=mock_chain):
            resp = await client.post(
                "/api/v1/patterns",
                json={"symbol": "AAPL", "timeframe": "H1"},
            )

        assert resp.status_code == 404

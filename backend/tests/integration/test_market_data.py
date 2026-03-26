from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.market_data import _get_caches, _get_chain
from app.core.models import OHLCVData
from app.main import app
from app.modules.data_acquisition.fallback_chain import DataProviderError

_SAMPLE_DATA = [
    OHLCVData(
        timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        open=1.10,
        high=1.15,
        low=1.05,
        close=1.12,
        volume=1000.0,
    )
]


@pytest.fixture
def mock_chain() -> AsyncMock:
    chain = AsyncMock()
    chain.fetch_ohlcv = AsyncMock(return_value=_SAMPLE_DATA)
    return chain


@pytest.fixture
async def api_client(mock_chain: AsyncMock):
    # Clear lru_cache singletons so each test starts fresh
    _get_caches.cache_clear()
    _get_chain.cache_clear()
    with patch("app.api.v1.market_data.get_fallback_chain", return_value=mock_chain):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    _get_caches.cache_clear()
    _get_chain.cache_clear()


class TestMarketDataEndpoint:
    @pytest.mark.asyncio
    async def test_success(self, api_client: AsyncClient, mock_chain: AsyncMock) -> None:
        resp = await api_client.get("/api/v1/market-data/EURUSD?timeframe=H1&period=30d")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["open"] == 1.10

    @pytest.mark.asyncio
    async def test_invalid_symbol(self, api_client: AsyncClient) -> None:
        resp = await api_client.get("/api/v1/market-data/INVALID!!!")
        assert resp.status_code == 400
        assert "Invalid symbol" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_period(self, api_client: AsyncClient) -> None:
        resp = await api_client.get("/api/v1/market-data/EURUSD?period=abc")
        assert resp.status_code == 400
        assert "Invalid period" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_provider_failure(self, api_client: AsyncClient, mock_chain: AsyncMock) -> None:
        mock_chain.fetch_ohlcv = AsyncMock(side_effect=DataProviderError("all failed"))
        resp = await api_client.get("/api/v1/market-data/EURUSD?timeframe=H1&period=30d")
        assert resp.status_code == 502

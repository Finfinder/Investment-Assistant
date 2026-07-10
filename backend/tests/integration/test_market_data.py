from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.market_data import _get_caches, _get_chain
from app.core.auth import require_auth
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

    # Mock Redis with in-memory storage
    _redis_store: dict[str, bytes] = {}

    async def _mock_get(key):
        return _redis_store.get(key)

    async def _mock_setex(key, ttl, value):
        _redis_store[key] = value if isinstance(value, bytes) else value.encode()

    async def _mock_delete(key):
        _redis_store.pop(key, None)

    async def _override_require_auth():
        return "dev"

    with (
        patch("app.modules.data_acquisition.redis_cache.redis_manager") as mock_manager,
        patch("app.api.v1.market_data.get_fallback_chain", return_value=mock_chain),
    ):
        mock_client = AsyncMock()
        mock_client.get = _mock_get
        mock_client.setex = _mock_setex
        mock_client.delete = _mock_delete
        mock_manager.client = mock_client
        app.dependency_overrides[require_auth] = _override_require_auth
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
        app.dependency_overrides.clear()

    _get_caches.cache_clear()
    _get_chain.cache_clear()


class TestMarketDataEndpoint:
    async def test_success(self, api_client: AsyncClient, mock_chain: AsyncMock) -> None:
        resp = await api_client.get("/api/v1/market-data/EURUSD?timeframe=H1&period=30d")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["open"] == 1.10

    async def test_invalid_symbol(self, api_client: AsyncClient) -> None:
        resp = await api_client.get("/api/v1/market-data/INVALID!!!")
        assert resp.status_code == 400
        assert "Invalid symbol" in resp.json()["error"]

    async def test_invalid_period(self, api_client: AsyncClient) -> None:
        resp = await api_client.get("/api/v1/market-data/EURUSD?period=abc")
        assert resp.status_code == 400
        assert "Invalid period" in resp.json()["error"]

    async def test_provider_failure(self, api_client: AsyncClient, mock_chain: AsyncMock) -> None:
        mock_chain.fetch_ohlcv = AsyncMock(side_effect=DataProviderError("all failed"))
        resp = await api_client.get("/api/v1/market-data/EURUSD?timeframe=H1&period=30d")
        assert resp.status_code == 502

    async def test_cache_hit(self, api_client: AsyncClient, mock_chain: AsyncMock) -> None:
        """Second request returns cached data without calling the provider again."""
        # First request - cache miss, provider called
        resp1 = await api_client.get("/api/v1/market-data/EURUSD?timeframe=H1&period=30d")
        assert resp1.status_code == 200
        assert mock_chain.fetch_ohlcv.call_count == 1

        # Second request - cache hit, provider NOT called again
        resp2 = await api_client.get("/api/v1/market-data/EURUSD?timeframe=H1&period=30d")
        assert resp2.status_code == 200
        assert mock_chain.fetch_ohlcv.call_count == 1  # still 1, not 2
        assert resp2.json() == resp1.json()

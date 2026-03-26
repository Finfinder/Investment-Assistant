from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.models import Timeframe
from app.modules.data_acquisition.providers.twelve_data_provider import (
    DAILY_RATE_LIMIT,
    TwelveDataProvider,
)


class TestTwelveDataProvider:
    def test_name_and_priority(self) -> None:
        provider = TwelveDataProvider(api_key="test_key")
        assert provider.name == "twelve_data"
        assert provider.priority == "secondary"

    def test_supported_symbols(self) -> None:
        provider = TwelveDataProvider(api_key="test_key")
        symbols = provider.get_supported_symbols()
        assert "EURUSD" in symbols
        assert "GOLD" in symbols

    @pytest.mark.asyncio
    async def test_is_available_no_key(self) -> None:
        provider = TwelveDataProvider(api_key="")
        assert await provider.is_available() is False

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_success(self) -> None:
        provider = TwelveDataProvider(api_key="test_key")

        mock_response = httpx.Response(
            200,
            json={
                "values": [
                    {
                        "datetime": "2024-01-02 10:00:00",
                        "open": "1.20",
                        "high": "1.25",
                        "low": "1.18",
                        "close": "1.22",
                        "volume": "5000",
                    },
                    {
                        "datetime": "2024-01-01 10:00:00",
                        "open": "1.10",
                        "high": "1.15",
                        "low": "1.08",
                        "close": "1.12",
                        "volume": "3000",
                    },
                ]
            },
            request=httpx.Request("GET", "https://api.twelvedata.com/time_series"),
        )

        with patch("app.modules.data_acquisition.providers.twelve_data_provider.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await provider.fetch_ohlcv("EURUSD", Timeframe.H1, "30d")

        assert len(result) == 2
        # Reversed to chronological order
        assert result[0].open == 1.10
        assert result[1].open == 1.20

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_rate_limit(self) -> None:
        provider = TwelveDataProvider(api_key="test_key")

        mock_response = httpx.Response(
            429,
            request=httpx.Request("GET", "https://api.twelvedata.com/time_series"),
        )

        with patch("app.modules.data_acquisition.providers.twelve_data_provider.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="rate limit"):
                await provider.fetch_ohlcv("EURUSD", Timeframe.H1, "30d")

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_daily_counter_exceeded(self) -> None:
        provider = TwelveDataProvider(api_key="test_key")
        provider._rate_limiter._request_count = DAILY_RATE_LIMIT

        with pytest.raises(RuntimeError, match="rate limit"):
            await provider.fetch_ohlcv("EURUSD", Timeframe.H1, "30d")

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_api_error(self) -> None:
        provider = TwelveDataProvider(api_key="test_key")

        mock_response = httpx.Response(
            200,
            json={"code": 400, "message": "Invalid symbol", "status": "error"},
            request=httpx.Request("GET", "https://api.twelvedata.com/time_series"),
        )

        with patch("app.modules.data_acquisition.providers.twelve_data_provider.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="Invalid symbol"):
                await provider.fetch_ohlcv("INVALID", Timeframe.H1, "30d")

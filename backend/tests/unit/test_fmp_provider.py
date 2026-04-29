from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.models import Timeframe
from app.modules.data_acquisition.providers.fmp_provider import (
    DAILY_RATE_LIMIT,
    FMPProvider,
    _resample_to_weekly,
)
from app.modules.data_acquisition.timeframes import DataTimeframe

FOREX_PAIRS_NEW = [
    "NZDUSD",
    "EURGBP",
    "EURJPY",
    "GBPJPY",
    "AUDCAD",
    "AUDCHF",
    "AUDJPY",
    "CADJPY",
    "CHFJPY",
    "EURCHF",
    "EURAUD",
    "EURCAD",
    "GBPCAD",
    "GBPCHF",
    "AUDNZD",
]


class TestFMPSymbolMapping:
    @pytest.mark.parametrize("pair", FOREX_PAIRS_NEW)
    def test_new_forex_pair_mapping(self, pair: str) -> None:
        provider = FMPProvider(api_key="test_key")
        assert provider._map_symbol(pair) == pair


class TestFMPProvider:
    def test_name_and_priority(self) -> None:
        provider = FMPProvider(api_key="test_key")
        assert provider.name == "fmp"
        assert provider.priority == "tertiary"

    def test_supported_symbols(self) -> None:
        provider = FMPProvider(api_key="test_key")
        symbols = provider.get_supported_symbols()
        assert "EURUSD" in symbols
        assert "GOLD" in symbols
        assert "US500" in symbols

    @pytest.mark.asyncio
    async def test_is_available_no_key(self) -> None:
        provider = FMPProvider(api_key="")
        assert await provider.is_available() is False

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_intraday_success(self) -> None:
        provider = FMPProvider(api_key="test_key")

        mock_response = httpx.Response(
            200,
            json=[
                {
                    "date": "2024-01-02 10:00:00",
                    "open": 1.20,
                    "high": 1.25,
                    "low": 1.18,
                    "close": 1.22,
                    "volume": 5000,
                },
                {
                    "date": "2024-01-01 10:00:00",
                    "open": 1.10,
                    "high": 1.15,
                    "low": 1.08,
                    "close": 1.12,
                    "volume": 3000,
                },
            ],
            request=httpx.Request("GET", "https://financialmodelingprep.com/api/v3/historical-chart/1hour/EURUSD"),
        )

        with patch("app.modules.data_acquisition.providers.fmp_provider.httpx.AsyncClient") as mock_client_cls:
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
    async def test_fetch_ohlcv_daily_success(self) -> None:
        provider = FMPProvider(api_key="test_key")

        mock_response = httpx.Response(
            200,
            json={
                "symbol": "EURUSD",
                "historical": [
                    {
                        "date": "2024-01-02",
                        "open": 1.20,
                        "high": 1.25,
                        "low": 1.18,
                        "close": 1.22,
                        "volume": 5000,
                    },
                ],
            },
            request=httpx.Request("GET", "https://financialmodelingprep.com/api/v3/historical-price-full/EURUSD"),
        )

        with patch("app.modules.data_acquisition.providers.fmp_provider.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await provider.fetch_ohlcv("EURUSD", Timeframe.D1, "30d")

        assert len(result) == 1
        assert result[0].open == 1.20

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_rate_limit_counter(self) -> None:
        provider = FMPProvider(api_key="test_key")
        provider._rate_limiter._request_count = DAILY_RATE_LIMIT

        with pytest.raises(RuntimeError, match="rate limit"):
            await provider.fetch_ohlcv("EURUSD", Timeframe.H1, "30d")

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_weekly_resamples_daily_data(self) -> None:
        provider = FMPProvider(api_key="test_key")

        mock_response = httpx.Response(
            200,
            json={
                "symbol": "EURUSD",
                "historical": [
                    {"date": "2024-01-12", "open": 1.40, "high": 1.45, "low": 1.38, "close": 1.42, "volume": 40},
                    {"date": "2024-01-11", "open": 1.30, "high": 1.35, "low": 1.28, "close": 1.32, "volume": 30},
                    {"date": "2024-01-05", "open": 1.20, "high": 1.25, "low": 1.18, "close": 1.22, "volume": 20},
                    {"date": "2024-01-04", "open": 1.10, "high": 1.15, "low": 1.08, "close": 1.12, "volume": 10},
                ],
            },
            request=httpx.Request("GET", "https://financialmodelingprep.com/api/v3/historical-price-full/EURUSD"),
        )

        with patch("app.modules.data_acquisition.providers.fmp_provider.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await provider.fetch_ohlcv("EURUSD", DataTimeframe.W1, "30d")

        assert len(result) == 2
        assert result[0].open == 1.10
        assert result[0].close == 1.22
        assert result[1].open == 1.30
        assert result[1].close == 1.42


def test_resample_to_weekly_returns_empty_for_empty_data() -> None:
    assert _resample_to_weekly([]) == []

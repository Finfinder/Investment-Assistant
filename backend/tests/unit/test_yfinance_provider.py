from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.core.models import OHLCVData, Timeframe
from app.modules.data_acquisition.providers.yfinance_provider import (
    SYMBOL_MAP,
    YFinanceProvider,
    _map_symbol,
    _resample_to_4h,
)
from app.modules.data_acquisition.timeframes import DataTimeframe


class TestSymbolMapping:
    def test_forex_mapping(self) -> None:
        assert _map_symbol("EURUSD") == "EURUSD=X"
        assert _map_symbol("GBPUSD") == "GBPUSD=X"

    def test_commodity_mapping(self) -> None:
        assert _map_symbol("GOLD") == "GC=F"
        assert _map_symbol("OIL") == "CL=F"

    def test_index_mapping(self) -> None:
        assert _map_symbol("US500") == "^GSPC"
        assert _map_symbol("DE40") == "^GDAXI"

    def test_unknown_symbol_passthrough(self) -> None:
        assert _map_symbol("AAPL") == "AAPL"

    def test_case_insensitive(self) -> None:
        assert _map_symbol("eurusd") == "EURUSD=X"

    def test_slash_stripped(self) -> None:
        assert _map_symbol("EUR/USD") == "EURUSD=X"

    @pytest.mark.parametrize(
        "pair",
        ["AUDCAD", "AUDCHF", "AUDJPY", "CADJPY", "CHFJPY", "EURCHF", "EURAUD", "EURCAD", "GBPCAD", "GBPCHF"],
    )
    def test_cross_pair_forex_mapping(self, pair: str) -> None:
        assert _map_symbol(pair) == f"{pair}=X"


class TestResampleTo4H:
    def test_resample_8_candles(self) -> None:
        candles = [
            OHLCVData(
                timestamp=datetime(2024, 1, 1, i, tzinfo=UTC),
                open=100.0 + i,
                high=102.0 + i,
                low=99.0 + i,
                close=101.0 + i,
                volume=1000.0,
            )
            for i in range(8)
        ]
        result = _resample_to_4h(candles)
        assert len(result) == 2
        assert result[0].open == candles[0].open
        assert result[0].close == candles[3].close
        assert result[0].high == max(c.high for c in candles[:4])
        assert result[0].low == min(c.low for c in candles[:4])
        assert result[0].volume == 4000.0

    def test_resample_incomplete_bucket_discarded(self) -> None:
        candles = [
            OHLCVData(
                timestamp=datetime(2024, 1, 1, i, tzinfo=UTC),
                open=100.0,
                high=102.0,
                low=99.0,
                close=101.0,
                volume=1000.0,
            )
            for i in range(5)
        ]
        result = _resample_to_4h(candles)
        assert len(result) == 1  # 4 used, 1 discarded

    def test_resample_empty(self) -> None:
        assert _resample_to_4h([]) == []


class TestYFinanceProvider:
    def test_name_and_priority(self) -> None:
        provider = YFinanceProvider()
        assert provider.name == "yfinance"
        assert provider.priority == "primary"

    def test_supported_symbols(self) -> None:
        provider = YFinanceProvider()
        symbols = provider.get_supported_symbols()
        assert "EURUSD" in symbols
        assert "GOLD" in symbols
        assert "US500" in symbols
        assert len(symbols) == len(SYMBOL_MAP)

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_success(self) -> None:
        provider = YFinanceProvider()

        mock_df = pd.DataFrame(
            {
                "Open": [1.1, 1.2],
                "High": [1.15, 1.25],
                "Low": [1.05, 1.15],
                "Close": [1.12, 1.22],
                "Volume": [1000, 2000],
            },
            index=pd.to_datetime(["2024-01-01 10:00:00+00:00", "2024-01-01 11:00:00+00:00"]),
        )

        mock_ticker = MagicMock()
        mock_ticker.history = MagicMock(return_value=mock_df)

        with patch(
            "app.modules.data_acquisition.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await provider.fetch_ohlcv("EURUSD", Timeframe.H1, "30d")

        assert len(result) == 2
        assert result[0].open == 1.1
        assert result[1].close == 1.22

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_empty_data(self) -> None:
        provider = YFinanceProvider()

        mock_ticker = MagicMock()
        mock_ticker.history = MagicMock(return_value=pd.DataFrame())

        with patch(
            "app.modules.data_acquisition.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await provider.fetch_ohlcv("EURUSD", Timeframe.H1, "30d")

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_weekly_uses_native_interval(self) -> None:
        provider = YFinanceProvider()

        mock_df = pd.DataFrame(
            {
                "Open": [1.1],
                "High": [1.15],
                "Low": [1.05],
                "Close": [1.12],
                "Volume": [1000],
            },
            index=pd.to_datetime(["2024-01-01 10:00:00+00:00"]),
        )

        mock_ticker = MagicMock()
        mock_ticker.history = MagicMock(return_value=mock_df)

        with patch(
            "app.modules.data_acquisition.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            await provider.fetch_ohlcv("EURUSD", DataTimeframe.W1, "30d")

        mock_ticker.history.assert_called_once_with(period="30d", interval="1wk")

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_timeout(self) -> None:
        provider = YFinanceProvider()

        mock_ticker = MagicMock()
        mock_ticker.history = MagicMock(side_effect=TimeoutError("Connection timed out"))

        with (
            patch(
                "app.modules.data_acquisition.providers.yfinance_provider.yf.Ticker",
                return_value=mock_ticker,
            ),
            pytest.raises(TimeoutError),
        ):
            await provider.fetch_ohlcv("EURUSD", Timeframe.H1, "30d")

    @pytest.mark.asyncio
    async def test_is_available_success(self) -> None:
        provider = YFinanceProvider()
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {"lastPrice": 150.0}

        with patch(
            "app.modules.data_acquisition.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await provider.is_available()

        assert result is True

    @pytest.mark.asyncio
    async def test_is_available_failure(self) -> None:
        provider = YFinanceProvider()

        with patch(
            "app.modules.data_acquisition.providers.yfinance_provider.yf.Ticker",
            side_effect=Exception("network error"),
        ):
            result = await provider.is_available()

        assert result is False

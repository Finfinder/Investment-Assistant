"""Tests for FRED data source."""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.modules.fundamental_analysis.data_sources.fred_source import FredSource

_MODULE = "app.modules.fundamental_analysis.data_sources.fred_source.asyncio.to_thread"


@pytest.fixture
def fred_source():
    return FredSource(api_key="test-key")


class TestFredSourceSuccess:
    @pytest.mark.asyncio
    async def test_fetch_series_returns_latest_value(self, fred_source: FredSource):
        mock_series = pd.Series([5.25, 5.33, 5.50])
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, return_value=mock_series):
            result = await fred_source.fetch_series("FEDFUNDS")
        assert result == 5.50

    @pytest.mark.asyncio
    async def test_fetch_indicator_maps_name_to_series(self, fred_source: FredSource):
        mock_series = pd.Series([3.5])
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, return_value=mock_series):
            result = await fred_source.fetch_indicator("fed_funds_rate")
        assert result == 3.5

    @pytest.mark.asyncio
    async def test_fetch_multiple_returns_dict(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, side_effect=[pd.Series([5.25]), pd.Series([300.0])]):
            result = await fred_source.fetch_multiple(["fed_funds_rate", "cpi_us"])
        assert result["fed_funds_rate"] == 5.25
        assert result["cpi_us"] == 300.0


class TestFredSourceErrors:
    @pytest.mark.asyncio
    async def test_fetch_series_returns_none_on_empty_data(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series(dtype=float)):
            result = await fred_source.fetch_series("FEDFUNDS")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_indicator_returns_none_for_unknown_name(self, fred_source: FredSource):
        result = await fred_source.fetch_indicator("nonexistent_indicator")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_series_returns_none_on_exception(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, side_effect=RuntimeError("API down")):
            result = await fred_source.fetch_series("FEDFUNDS")
        assert result is None


class TestFredSourceCaching:
    @pytest.mark.asyncio
    async def test_cached_value_is_returned_without_api_call(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([5.25])) as mock_to_thread:
            # First call hits API
            result1 = await fred_source.fetch_series("FEDFUNDS")
            assert result1 == 5.25
            assert mock_to_thread.call_count == 1

            # Second call should use cache
            result2 = await fred_source.fetch_series("FEDFUNDS")
            assert result2 == 5.25
            assert mock_to_thread.call_count == 1  # no additional call

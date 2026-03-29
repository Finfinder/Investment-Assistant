"""Tests for FRED data source."""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.modules.fundamental_analysis.data_sources.fred_source import (
    FRED_SERIES,
    SERIES_LOOKBACK_DAYS,
    SERIES_YOY_UNITS,
    FredSource,
)

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


class TestFredSourceUnitsTransform:
    """Series in SERIES_YOY_UNITS get units kwarg; others do not."""

    @pytest.mark.asyncio
    async def test_index_series_passes_units_pc1(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        series_id = "CP0000EZ19M086NEST"
        assert series_id in SERIES_YOY_UNITS

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([1.9])) as mock_to_thread:
            result = await fred_source.fetch_series(series_id)

        assert result == 1.9
        _, kwargs = mock_to_thread.call_args
        assert kwargs.get("units") == "pc1"

    @pytest.mark.asyncio
    async def test_regular_series_has_no_units_kwarg(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([5.25])) as mock_to_thread:
            await fred_source.fetch_series("FEDFUNDS")

        _, kwargs = mock_to_thread.call_args
        assert "units" not in kwargs

    @pytest.mark.asyncio
    async def test_fetch_indicator_cpi_eu_returns_yoy_value(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([1.9])):
            result = await fred_source.fetch_indicator("cpi_eu")
        assert result == 1.9

    @pytest.mark.asyncio
    async def test_cache_works_for_units_transformed_series(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([2.1])) as mock_to_thread:
            result1 = await fred_source.fetch_series("CP0000EZ19M086NEST")
            result2 = await fred_source.fetch_series("CP0000EZ19M086NEST")

        assert result1 == 2.1
        assert result2 == 2.1
        assert mock_to_thread.call_count == 1


class TestFredSourceLookbackOverride:
    """Series in SERIES_LOOKBACK_DAYS get wider lookback window; others use the default."""

    @pytest.mark.asyncio
    async def test_annual_series_uses_730_day_lookback(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        series_id = "FPCPITOTLZGJPN"
        assert series_id in SERIES_LOOKBACK_DAYS

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([2.74])) as mock_to_thread:
            result = await fred_source.fetch_series(series_id)

        assert result == 2.74
        call_args = mock_to_thread.call_args
        observation_start = call_args.kwargs.get("observation_start") or call_args[1]["observation_start"]
        observation_end = call_args.kwargs.get("observation_end") or call_args[1]["observation_end"]
        lookback = (observation_end - observation_start).days
        assert 729 <= lookback <= 731

    @pytest.mark.asyncio
    async def test_default_lookback_for_regular_series(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([5.25])) as mock_to_thread:
            await fred_source.fetch_series("FEDFUNDS")

        call_args = mock_to_thread.call_args
        observation_start = call_args.kwargs.get("observation_start") or call_args[1]["observation_start"]
        observation_end = call_args.kwargs.get("observation_end") or call_args[1]["observation_end"]
        lookback = (observation_end - observation_start).days
        assert 364 <= lookback <= 366


class TestFredSourceSeriesMappings:
    """Verify critical CPI series mappings after OECD discontinuation fix."""

    def test_cpi_jp_maps_to_imf_annual_series(self):
        assert FRED_SERIES["cpi_jp"] == "FPCPITOTLZGJPN"

    def test_cpi_au_maps_to_oecd_quarterly_series(self):
        assert FRED_SERIES["cpi_au"] == "CPALTT01AUQ659N"

"""Tests for FRED data source."""

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from cachetools import TTLCache
from tenacity import wait_none

from app.modules.fundamental_analysis.data_sources.fred_source import (
    FRED_SERIES,
    FRED_SERIES_FALLBACKS,
    SERIES_LOOKBACK_DAYS,
    SERIES_YOY_UNITS,
    FredSource,
)
from app.modules.fundamental_analysis.data_sources.macro_observation import MacroObservation

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
        assert result == pytest.approx(5.50)

    @pytest.mark.asyncio
    async def test_fetch_indicator_maps_name_to_series(self, fred_source: FredSource):
        mock_series = pd.Series([3.5])
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, return_value=mock_series):
            result = await fred_source.fetch_indicator("fed_funds_rate")
        assert result == pytest.approx(3.5)

    @pytest.mark.asyncio
    async def test_fetch_multiple_returns_dict(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, side_effect=[pd.Series([5.25]), pd.Series([300.0])]):
            result = await fred_source.fetch_multiple(["fed_funds_rate", "cpi_us"])
        assert result["fed_funds_rate"] == pytest.approx(5.25)
        assert result["cpi_us"] == pytest.approx(300.0)


class TestFredSourceObservation:
    @pytest.mark.asyncio
    async def test_fetch_series_observation_returns_value_and_period(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        series = pd.Series(
            [5.25, 5.5],
            index=pd.to_datetime(["2025-03-01", "2025-04-01"]),
        )

        with patch(_MODULE, new_callable=AsyncMock, return_value=series):
            observation = await fred_source.fetch_series_observation("FEDFUNDS")

        assert observation is not None
        assert observation.value == pytest.approx(5.5)
        assert str(observation.period) == "2025-04-01"
        assert observation.source == "fred"

    @pytest.mark.asyncio
    async def test_fetch_indicator_observation_uses_fallback_chain(self, fred_source: FredSource):
        with patch.object(
            fred_source,
            "fetch_series_observation",
            new_callable=AsyncMock,
            side_effect=[None, None],
        ) as mock_fetch:
            result = await fred_source.fetch_indicator_observation("cpi_au")

        assert result is None
        assert mock_fetch.await_args_list[0].args == ("CPALTT01AUQ659N", 365)
        assert mock_fetch.await_args_list[1].args == ("FPCPITOTLZGAUS", 365)


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

    @pytest.mark.asyncio
    async def test_fetch_series_returns_none_on_all_nan_data(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([float("nan")])):
            result = await fred_source.fetch_series("FEDFUNDS")

        assert result is None

    @pytest.mark.asyncio
    async def test_error_log_sanitizes_api_key(self, fred_source: FredSource, caplog):
        """logger.error must not expose the FRED API key when an exception URL is logged."""
        import logging

        fred_source._fred = MagicMock()
        exc_msg = "https://api.stlouisfed.org/series?api_key=SUPER_SECRET&series_id=FEDFUNDS"

        with patch(_MODULE, new_callable=AsyncMock, side_effect=RuntimeError(exc_msg)), caplog.at_level(logging.ERROR):
            result = await fred_source.fetch_series("FEDFUNDS")

        assert result is None
        assert "SUPER_SECRET" not in caplog.text
        assert "api_key=***" in caplog.text


class TestFredSourceCaching:
    @pytest.mark.asyncio
    async def test_cached_value_is_returned_without_api_call(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([5.25])) as mock_to_thread:
            # First call hits API
            result1 = await fred_source.fetch_series("FEDFUNDS")
            assert result1 == pytest.approx(5.25)
            assert mock_to_thread.call_count == 1

            # Second call should use cache
            result2 = await fred_source.fetch_series("FEDFUNDS")
            assert result2 == pytest.approx(5.25)
            assert mock_to_thread.call_count == 1  # no additional call

    @pytest.mark.asyncio
    async def test_negative_cache_is_returned_without_api_call_after_empty_data(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series(dtype=float)) as mock_to_thread:
            result1 = await fred_source.fetch_series("FEDFUNDS")
            result2 = await fred_source.fetch_series("FEDFUNDS")

        assert result1 is None
        assert result2 is None
        assert mock_to_thread.call_count == 1

    @pytest.mark.asyncio
    async def test_negative_cache_hit_skips_fred_client_initialization(self, fred_source: FredSource):
        fred_source._negative_cache["fred:FEDFUNDS"] = object()

        with patch.object(fred_source, "_get_fred", side_effect=AssertionError("_get_fred should not be called")):
            result = await fred_source.fetch_series("FEDFUNDS")

        assert result is None

    @pytest.mark.asyncio
    async def test_negative_cache_expires_and_allows_recovery(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        fred_source._negative_cache = TTLCache(maxsize=64, ttl=0.01)

        with patch(
            _MODULE,
            new_callable=AsyncMock,
            side_effect=[pd.Series(dtype=float), pd.Series([5.25])],
        ) as mock_to_thread:
            result1 = await fred_source.fetch_series("FEDFUNDS")
            await asyncio.sleep(0.02)
            result2 = await fred_source.fetch_series("FEDFUNDS")

        assert result1 is None
        assert result2 == pytest.approx(5.25)
        assert mock_to_thread.call_count == 2

    @pytest.mark.asyncio
    async def test_zero_value_is_cached_as_valid_positive_value(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([0.0])) as mock_to_thread:
            result1 = await fred_source.fetch_series("FEDFUNDS")
            result2 = await fred_source.fetch_series("FEDFUNDS")

        assert result1 == pytest.approx(0.0)
        assert result2 == pytest.approx(0.0)
        assert mock_to_thread.call_count == 1


class TestFredSourceUnitsTransform:
    """Series in SERIES_YOY_UNITS get units kwarg; others do not."""

    @pytest.mark.asyncio
    async def test_index_series_passes_units_pc1(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        series_id = "CP0000EZ19M086NEST"
        assert series_id in SERIES_YOY_UNITS

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([1.9])) as mock_to_thread:
            result = await fred_source.fetch_series(series_id)

        assert result == pytest.approx(1.9)
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
        assert result == pytest.approx(1.9)

    @pytest.mark.asyncio
    async def test_cache_works_for_units_transformed_series(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([2.1])) as mock_to_thread:
            result1 = await fred_source.fetch_series("CP0000EZ19M086NEST")
            result2 = await fred_source.fetch_series("CP0000EZ19M086NEST")

        assert result1 == pytest.approx(2.1)
        assert result2 == pytest.approx(2.1)
        assert mock_to_thread.call_count == 1

    @pytest.mark.asyncio
    async def test_nz_cpi_index_passes_units_pc1(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        series_id = "NZLCPIALLQINMEI"
        assert series_id in SERIES_YOY_UNITS

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([2.5])) as mock_to_thread:
            result = await fred_source.fetch_series(series_id)

        assert result == pytest.approx(2.5)
        _, kwargs = mock_to_thread.call_args
        assert kwargs.get("units") == "pc1"


class TestFredSourceLookbackOverride:
    """Series in SERIES_LOOKBACK_DAYS get wider lookback window; others use the default."""

    @pytest.mark.asyncio
    async def test_annual_series_uses_730_day_lookback(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        series_id = "FPCPITOTLZGJPN"
        assert series_id in SERIES_LOOKBACK_DAYS

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([2.74])) as mock_to_thread:
            result = await fred_source.fetch_series(series_id)

        assert result == pytest.approx(2.74)
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

    @pytest.mark.asyncio
    async def test_quarterly_nz_cpi_uses_540_day_lookback(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        series_id = "NZLCPIALLQINMEI"
        assert series_id in SERIES_LOOKBACK_DAYS

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([2.5])) as mock_to_thread:
            result = await fred_source.fetch_series(series_id)

        assert result == pytest.approx(2.5)
        call_args = mock_to_thread.call_args
        observation_start = call_args.kwargs.get("observation_start") or call_args[1]["observation_start"]
        observation_end = call_args.kwargs.get("observation_end") or call_args[1]["observation_end"]
        lookback = (observation_end - observation_start).days
        assert 539 <= lookback <= 541

    @pytest.mark.asyncio
    async def test_uk_cpi_uses_540_day_lookback(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        series_id = "CPALTT01GBM659N"
        assert series_id in SERIES_LOOKBACK_DAYS

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([3.4])) as mock_to_thread:
            result = await fred_source.fetch_series(series_id)

        assert result == pytest.approx(3.4)
        call_args = mock_to_thread.call_args
        observation_start = call_args.kwargs.get("observation_start") or call_args[1]["observation_start"]
        observation_end = call_args.kwargs.get("observation_end") or call_args[1]["observation_end"]
        lookback = (observation_end - observation_start).days
        assert 539 <= lookback <= 541

    @pytest.mark.asyncio
    async def test_quarterly_au_cpi_uses_540_day_lookback(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        series_id = "CPALTT01AUQ659N"
        assert series_id in SERIES_LOOKBACK_DAYS

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([2.4])) as mock_to_thread:
            result = await fred_source.fetch_series(series_id)

        assert result == pytest.approx(2.4)
        call_args = mock_to_thread.call_args
        observation_start = call_args.kwargs.get("observation_start") or call_args[1]["observation_start"]
        observation_end = call_args.kwargs.get("observation_end") or call_args[1]["observation_end"]
        lookback = (observation_end - observation_start).days
        assert 539 <= lookback <= 541

    @pytest.mark.asyncio
    async def test_quarterly_us_gdp_uses_540_day_lookback(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        series_id = "GDP"
        assert series_id in SERIES_LOOKBACK_DAYS

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([31856.257])) as mock_to_thread:
            result = await fred_source.fetch_series(series_id)

        assert result == pytest.approx(31856.257)
        call_args = mock_to_thread.call_args
        observation_start = call_args.kwargs.get("observation_start") or call_args[1]["observation_start"]
        observation_end = call_args.kwargs.get("observation_end") or call_args[1]["observation_end"]
        lookback = (observation_end - observation_start).days
        assert 539 <= lookback <= 541

    @pytest.mark.asyncio
    async def test_annual_au_cpi_fallback_uses_730_day_lookback(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        series_id = "FPCPITOTLZGAUS"
        assert series_id in SERIES_LOOKBACK_DAYS

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([3.16])) as mock_to_thread:
            result = await fred_source.fetch_series(series_id)

        assert result == pytest.approx(3.16)
        call_args = mock_to_thread.call_args
        observation_start = call_args.kwargs.get("observation_start") or call_args[1]["observation_start"]
        observation_end = call_args.kwargs.get("observation_end") or call_args[1]["observation_end"]
        lookback = (observation_end - observation_start).days
        assert 729 <= lookback <= 731

    @pytest.mark.asyncio
    async def test_ca_cpi_uses_540_day_lookback(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        series_id = "CPALTT01CAM659N"
        assert series_id in SERIES_LOOKBACK_DAYS

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([2.32])) as mock_to_thread:
            result = await fred_source.fetch_series(series_id)

        assert result == pytest.approx(2.32)
        call_args = mock_to_thread.call_args
        observation_start = call_args.kwargs.get("observation_start") or call_args[1]["observation_start"]
        observation_end = call_args.kwargs.get("observation_end") or call_args[1]["observation_end"]
        lookback = (observation_end - observation_start).days
        assert 539 <= lookback <= 541

    @pytest.mark.asyncio
    async def test_us_cpi_uses_540_day_lookback(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        series_id = "CPALTT01USM659N"
        assert series_id in SERIES_LOOKBACK_DAYS

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([2.31])) as mock_to_thread:
            result = await fred_source.fetch_series(series_id)

        assert result == pytest.approx(2.31)
        call_args = mock_to_thread.call_args
        observation_start = call_args.kwargs.get("observation_start") or call_args[1]["observation_start"]
        observation_end = call_args.kwargs.get("observation_end") or call_args[1]["observation_end"]
        lookback = (observation_end - observation_start).days
        assert 539 <= lookback <= 541

    @pytest.mark.asyncio
    async def test_ch_cpi_uses_540_day_lookback(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        series_id = "CPALTT01CHM659N"
        assert series_id in SERIES_LOOKBACK_DAYS

        with patch(_MODULE, new_callable=AsyncMock, return_value=pd.Series([0.03])) as mock_to_thread:
            result = await fred_source.fetch_series(series_id)

        assert result == pytest.approx(0.03)
        call_args = mock_to_thread.call_args
        observation_start = call_args.kwargs.get("observation_start") or call_args[1]["observation_start"]
        observation_end = call_args.kwargs.get("observation_end") or call_args[1]["observation_end"]
        lookback = (observation_end - observation_start).days
        assert 539 <= lookback <= 541


class TestFredSourceSeriesMappings:
    """Verify critical FRED series mappings after JP CPI moved to OECD."""

    def test_cpi_jp_not_mapped_in_fred_source(self):
        assert "cpi_jp" not in FRED_SERIES

    def test_cpi_au_maps_to_oecd_quarterly_series(self):
        assert FRED_SERIES["cpi_au"] == "CPALTT01AUQ659N"

    def test_cpi_au_has_world_bank_annual_fallback_series(self):
        assert FRED_SERIES_FALLBACKS["cpi_au"] == ("FPCPITOTLZGAUS",)

    def test_cpi_nz_maps_to_oecd_quarterly_index_series(self):
        assert FRED_SERIES["cpi_nz"] == "NZLCPIALLQINMEI"

    def test_rbnz_rate_maps_to_3month_interbank_series(self):
        # IRSTCI01NZM156N (overnight) discontinued Jan 2025 — replaced by 3-month interbank rate
        assert FRED_SERIES["rbnz_rate"] == "IR3TIB01NZM156N"

    def test_snb_rate_maps_to_3month_interbank_series(self):
        # IRSTCI01CHM156N (overnight) discontinued Apr 2024 — replaced by 3-month interbank rate
        assert FRED_SERIES["snb_rate"] == "IR3TIB01CHM156N"


class TestFredSourceIndicatorFallbacks:
    """Verify per-indicator fallback order for FRED series."""

    @pytest.mark.asyncio
    async def test_cpi_au_primary_success_skips_fallback(self, fred_source: FredSource):
        with patch.object(
            fred_source,
            "fetch_series_observation",
            new_callable=AsyncMock,
            return_value=MacroObservation(value=2.4, period=date(2026, 4, 1), source="fred"),
        ) as mock_fetch_series:
            result = await fred_source.fetch_indicator("cpi_au")

        assert result == pytest.approx(2.4)
        mock_fetch_series.assert_awaited_once_with("CPALTT01AUQ659N", 365)

    @pytest.mark.asyncio
    async def test_cpi_au_empty_primary_uses_world_bank_fallback(self, fred_source: FredSource):
        with patch.object(
            fred_source,
            "fetch_series_observation",
            new_callable=AsyncMock,
            side_effect=[None, MacroObservation(value=3.16, period=date(2026, 4, 1), source="fred")],
        ) as mock_fetch_series:
            result = await fred_source.fetch_indicator("cpi_au")

        assert result == pytest.approx(3.16)
        assert mock_fetch_series.await_args_list[0].args == ("CPALTT01AUQ659N", 365)
        assert mock_fetch_series.await_args_list[1].args == ("FPCPITOTLZGAUS", 365)

    @pytest.mark.asyncio
    async def test_cpi_au_handled_primary_error_uses_world_bank_fallback(self, fred_source: FredSource):
        with patch.object(
            fred_source,
            "fetch_series_observation",
            new_callable=AsyncMock,
            side_effect=[None, MacroObservation(value=3.16, period=date(2026, 4, 1), source="fred")],
        ) as mock_fetch_series:
            result = await fred_source.fetch_indicator("cpi_au")

        assert result == pytest.approx(3.16)
        assert mock_fetch_series.await_count == 2

    @pytest.mark.asyncio
    async def test_cpi_au_all_series_missing_returns_none(self, fred_source: FredSource):
        with patch.object(
            fred_source,
            "fetch_series_observation",
            new_callable=AsyncMock,
            side_effect=[None, None],
        ) as mock_fetch_series:
            result = await fred_source.fetch_indicator("cpi_au")

        assert result is None
        assert mock_fetch_series.await_count == 2

    @pytest.mark.asyncio
    async def test_regular_indicator_missing_data_does_not_use_fallback(self, fred_source: FredSource):
        with patch.object(
            fred_source,
            "fetch_series_observation",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_fetch_series:
            result = await fred_source.fetch_indicator("fed_funds_rate")

        assert result is None
        mock_fetch_series.assert_awaited_once_with("FEDFUNDS", 365)


class TestFredSourceRetry:
    """Verify retry behaviour for transient FRED API errors."""

    @pytest.fixture(autouse=True)
    def fast_retry(self):
        """Replace exponential wait with no-wait so tests don't actually sleep."""
        original_wait = FredSource._fetch_from_api.retry.wait  # type: ignore[attr-defined]
        FredSource._fetch_from_api.retry.wait = wait_none()  # type: ignore[attr-defined]
        yield
        FredSource._fetch_from_api.retry.wait = original_wait  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_transient_failure(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        side_effects = [ConnectionError("transient network error"), pd.Series([5.25])]

        with patch(_MODULE, new_callable=AsyncMock, side_effect=side_effects) as mock_to_thread:
            result = await fred_source.fetch_series("FEDFUNDS")

        assert result == pytest.approx(5.25)
        assert mock_to_thread.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_exhausted_returns_none(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        side_effects = [ConnectionError("err1"), ConnectionError("err2"), ConnectionError("err3")]

        with patch(_MODULE, new_callable=AsyncMock, side_effect=side_effects) as mock_to_thread:
            result = await fred_source.fetch_series("FEDFUNDS")

        assert result is None
        assert mock_to_thread.call_count == 3

    @pytest.mark.asyncio
    async def test_negative_cache_is_returned_after_retry_exhaustion(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        side_effects = [ConnectionError("err1"), ConnectionError("err2"), ConnectionError("err3")]

        with patch(_MODULE, new_callable=AsyncMock, side_effect=side_effects) as mock_to_thread:
            result1 = await fred_source.fetch_series("FEDFUNDS")
            result2 = await fred_source.fetch_series("FEDFUNDS")

        assert result1 is None
        assert result2 is None
        assert mock_to_thread.call_count == 3

    @pytest.mark.asyncio
    async def test_permanent_error_not_retried(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, side_effect=ValueError("bad series")) as mock_to_thread:
            result = await fred_source.fetch_series("FEDFUNDS")

        assert result is None
        assert mock_to_thread.call_count == 1

    @pytest.mark.asyncio
    async def test_negative_cache_is_returned_after_permanent_error(self, fred_source: FredSource):
        fred_source._fred = MagicMock()

        with patch(_MODULE, new_callable=AsyncMock, side_effect=ValueError("bad series")) as mock_to_thread:
            result1 = await fred_source.fetch_series("FEDFUNDS")
            result2 = await fred_source.fetch_series("FEDFUNDS")

        assert result1 is None
        assert result2 is None
        assert mock_to_thread.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_does_not_affect_cache(self, fred_source: FredSource):
        fred_source._fred = MagicMock()
        side_effects = [ConnectionError("transient"), pd.Series([5.25])]

        with patch(_MODULE, new_callable=AsyncMock, side_effect=side_effects) as mock_to_thread:
            result1 = await fred_source.fetch_series("FEDFUNDS")
            result2 = await fred_source.fetch_series("FEDFUNDS")

        assert result1 == pytest.approx(5.25)
        assert result2 == pytest.approx(5.25)
        assert mock_to_thread.call_count == 2  # retry consumed 2 calls; cache served call 2

    def test_before_sleep_log_sanitizes_api_key(self, caplog):
        """_before_sleep_log must redact api_key from exception messages in retry logs."""
        import logging

        from app.modules.fundamental_analysis.data_sources.fred_source import _before_sleep_log

        exc = ConnectionError("https://api.stlouisfed.org/series?api_key=SUPER_SECRET&series_id=FEDFUNDS")
        outcome_mock = MagicMock()
        outcome_mock.exception.return_value = exc
        retry_state_mock = MagicMock()
        retry_state_mock.outcome = outcome_mock
        retry_state_mock.attempt_number = 1

        with caplog.at_level(logging.WARNING):
            _before_sleep_log(retry_state_mock)

        assert "SUPER_SECRET" not in caplog.text
        assert "api_key=***" in caplog.text

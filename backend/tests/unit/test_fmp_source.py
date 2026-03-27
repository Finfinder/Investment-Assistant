"""Tests for FMP economic data source and COT reports."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from pytest import approx

from app.modules.fundamental_analysis.data_sources.fmp_source import FmpEconomicSource


@pytest.fixture
def fmp_source():
    return FmpEconomicSource(api_key="test-key")


class TestFmpTreasuryRates:
    async def test_fetch_treasury_rates_success(self, fmp_source: FmpEconomicSource):
        treasury_data = [
            {
                "date": "2024-01-15",
                "month1": 5.38,
                "month3": 5.35,
                "month6": 5.28,
                "year1": 4.98,
                "year2": 4.35,
                "year5": 4.05,
                "year10": 4.12,
                "year30": 4.35,
            }
        ]
        fmp_source._get = AsyncMock(return_value=treasury_data)

        result = await fmp_source.fetch_treasury_rates()

        assert result["treasury_10y"] == approx(4.12)
        assert result["treasury_2y"] == approx(4.35)

    async def test_fetch_treasury_rates_empty_response(self, fmp_source: FmpEconomicSource):
        fmp_source._get = AsyncMock(return_value=[])

        result = await fmp_source.fetch_treasury_rates()

        assert result == {}

    async def test_fetch_economic_indicator_success(self, fmp_source: FmpEconomicSource):
        fmp_source._get = AsyncMock(return_value=[{"date": "2024-01-01", "value": 3.4}])

        result = await fmp_source.fetch_economic_indicator("CPI")

        assert result == approx(3.4)


class TestFmpCotReports:
    async def test_fetch_cot_report_success(self, fmp_source: FmpEconomicSource):
        cot_data = [
            {
                "date": "2024-01-15",
                "commercialLong": 200000,
                "commercialShort": 180000,
                "nonCommercialLong": 150000,
                "nonCommercialShort": 120000,
                "nonReportableLong": 30000,
                "nonReportableShort": 25000,
            },
            {
                "date": "2024-01-08",
                "commercialLong": 195000,
                "commercialShort": 185000,
                "nonCommercialLong": 140000,
                "nonCommercialShort": 125000,
                "nonReportableLong": 28000,
                "nonReportableShort": 26000,
            },
        ]
        fmp_source._get = AsyncMock(return_value=cot_data)

        result = await fmp_source.fetch_cot_report("GC")

        assert result is not None
        assert result["net_commercial"] == 20000  # 200000 - 180000
        assert result["net_non_commercial"] == 30000  # 150000 - 120000
        assert result["net_non_reportable"] == 5000  # 30000 - 25000
        # Week-over-week change: 30000 - (140000-125000) = 30000 - 15000 = 15000
        assert result["net_non_commercial_change"] == 15000

    async def test_fetch_cot_report_no_data(self, fmp_source: FmpEconomicSource):
        fmp_source._get = AsyncMock(return_value=[])

        result = await fmp_source.fetch_cot_report("UNKNOWN")

        assert result is None


class TestFmpRateLimit:
    async def test_rate_limit_raises_on_get(self, fmp_source: FmpEconomicSource):
        fmp_source._rate_limiter._request_count = 250

        with pytest.raises(RuntimeError, match="rate limit"):
            await fmp_source._get("/v4/treasury")


class TestFmpGetMethod:
    """Tests for the _get method covering caching, HTTP errors, and 429 handling."""

    @pytest.mark.asyncio
    async def test_get_caches_response(self, fmp_source: FmpEconomicSource):
        """Second call with same path returns cached value without HTTP request."""

        mock_response = httpx.Response(
            200,
            json=[{"value": 42}],
            request=httpx.Request("GET", "https://financialmodelingprep.com/api/v4/test"),
        )

        with patch("app.modules.fundamental_analysis.data_sources.fmp_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result1 = await fmp_source._get("/v4/test")
            result2 = await fmp_source._get("/v4/test")

        assert result1 == [{"value": 42}]
        assert result2 == [{"value": 42}]
        # Only one HTTP call — second was served from cache
        assert mock_client.get.await_count == 1

    @pytest.mark.asyncio
    async def test_get_raises_on_429(self, fmp_source: FmpEconomicSource):
        """HTTP 429 response raises RuntimeError."""

        mock_response = httpx.Response(
            429,
            request=httpx.Request("GET", "https://financialmodelingprep.com/api/v4/test"),
        )

        with patch("app.modules.fundamental_analysis.data_sources.fmp_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="rate limit"):
                await fmp_source._get("/v4/test-429")

    @pytest.mark.asyncio
    async def test_get_raises_on_http_error(self, fmp_source: FmpEconomicSource):
        """Non-429 HTTP error raises httpx.HTTPStatusError."""

        mock_response = httpx.Response(
            500,
            request=httpx.Request("GET", "https://financialmodelingprep.com/api/v4/test"),
        )

        with patch("app.modules.fundamental_analysis.data_sources.fmp_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await fmp_source._get("/v4/test-500")

    @pytest.mark.asyncio
    async def test_get_passes_extra_params(self, fmp_source: FmpEconomicSource):
        """Extra params are merged with apikey param."""

        mock_response = httpx.Response(
            200,
            json={"ok": True},
            request=httpx.Request("GET", "https://financialmodelingprep.com/api/v4/test"),
        )

        with patch("app.modules.fundamental_analysis.data_sources.fmp_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            await fmp_source._get("/v4/data", params={"name": "CPI"})

        call_kwargs = mock_client.get.call_args
        assert "apikey" in call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))


class TestFmpEconomicIndicatorEdgeCases:
    """Edge cases for fetch_economic_indicator."""

    @pytest.mark.asyncio
    async def test_fetch_economic_indicator_returns_none_on_non_list(self, fmp_source: FmpEconomicSource):
        fmp_source._get = AsyncMock(return_value={"error": "bad"})
        result = await fmp_source.fetch_economic_indicator("CPI")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_economic_indicator_returns_none_on_empty(self, fmp_source: FmpEconomicSource):
        fmp_source._get = AsyncMock(return_value=[])
        result = await fmp_source.fetch_economic_indicator("CPI")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_economic_indicator_returns_none_on_exception(self, fmp_source: FmpEconomicSource):
        fmp_source._get = AsyncMock(side_effect=RuntimeError("API down"))
        result = await fmp_source.fetch_economic_indicator("CPI")
        assert result is None


class TestFmpTreasuryRatesEdgeCases:
    """Edge cases for fetch_treasury_rates."""

    @pytest.mark.asyncio
    async def test_fetch_treasury_rates_returns_empty_on_exception(self, fmp_source: FmpEconomicSource):
        fmp_source._get = AsyncMock(side_effect=RuntimeError("API down"))
        result = await fmp_source.fetch_treasury_rates()
        assert result == {}

    @pytest.mark.asyncio
    async def test_fetch_treasury_rates_dict_response(self, fmp_source: FmpEconomicSource):
        """When API returns a dict instead of list, it should still parse."""
        fmp_source._get = AsyncMock(return_value={"year10": 4.0, "year2": 3.5})
        result = await fmp_source.fetch_treasury_rates()
        assert result["treasury_10y"] == approx(4.0)
        assert result["treasury_2y"] == approx(3.5)


class TestFmpEconomicCalendar:
    """Tests for fetch_economic_calendar."""

    @pytest.mark.asyncio
    async def test_fetch_economic_calendar_success(self, fmp_source: FmpEconomicSource):
        fmp_source._get = AsyncMock(return_value=[
            {"country": "US", "event": "CPI Release"},
            {"country": "EU", "event": "ECB Rate Decision"},
            {"country": "US", "event": "NFP"},
        ])
        result = await fmp_source.fetch_economic_calendar("US")
        assert len(result) == 2
        assert all(e["country"] == "US" for e in result)

    @pytest.mark.asyncio
    async def test_fetch_economic_calendar_empty(self, fmp_source: FmpEconomicSource):
        fmp_source._get = AsyncMock(return_value=[])
        result = await fmp_source.fetch_economic_calendar()
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_economic_calendar_returns_empty_on_exception(self, fmp_source: FmpEconomicSource):
        fmp_source._get = AsyncMock(side_effect=RuntimeError("fail"))
        result = await fmp_source.fetch_economic_calendar()
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_economic_calendar_non_list_response(self, fmp_source: FmpEconomicSource):
        fmp_source._get = AsyncMock(return_value=None)
        result = await fmp_source.fetch_economic_calendar()
        assert result == []


class TestFmpCotReportEdgeCases:
    """Edge cases for fetch_cot_report."""

    @pytest.mark.asyncio
    async def test_fetch_cot_report_single_entry_no_previous(self, fmp_source: FmpEconomicSource):
        """COT report with only one entry — no week-over-week change."""
        cot_data = [
            {
                "date": "2024-01-15",
                "commercialLong": 200000,
                "commercialShort": 180000,
                "nonCommercialLong": 150000,
                "nonCommercialShort": 120000,
                "nonReportableLong": 30000,
                "nonReportableShort": 25000,
            },
        ]
        fmp_source._get = AsyncMock(return_value=cot_data)
        result = await fmp_source.fetch_cot_report("GC")
        assert result is not None
        assert "net_non_commercial_change" not in result

    @pytest.mark.asyncio
    async def test_fetch_cot_report_returns_none_on_exception(self, fmp_source: FmpEconomicSource):
        fmp_source._get = AsyncMock(side_effect=RuntimeError("API down"))
        result = await fmp_source.fetch_cot_report("GC")
        assert result is None

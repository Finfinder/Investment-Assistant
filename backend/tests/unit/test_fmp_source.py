"""Tests for FMP economic data source and COT reports."""

from unittest.mock import AsyncMock

import pytest

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

        assert result["treasury_10y"] == 4.12
        assert result["treasury_2y"] == 4.35

    async def test_fetch_treasury_rates_empty_response(self, fmp_source: FmpEconomicSource):
        fmp_source._get = AsyncMock(return_value=[])

        result = await fmp_source.fetch_treasury_rates()

        assert result == {}

    async def test_fetch_economic_indicator_success(self, fmp_source: FmpEconomicSource):
        fmp_source._get = AsyncMock(return_value=[{"date": "2024-01-01", "value": 3.4}])

        result = await fmp_source.fetch_economic_indicator("CPI")

        assert result == 3.4


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

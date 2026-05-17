"""Tests for BLS CPI source."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.fundamental_analysis.data_sources.bls_cpi_source import BlsCpiSource


@pytest.fixture
def bls_source():
    return BlsCpiSource()


class TestBlsExtractObservation:
    def test_extract_observation_computes_yoy_and_ignores_non_monthly_periods(self, bls_source: BlsCpiSource):
        payload = {
            "Results": {
                "series": [
                    {
                        "data": [
                            {"year": "2025", "period": "M03", "value": "312.332"},
                            {"year": "2024", "period": "M03", "value": "303.123"},
                            {"year": "2025", "period": "M13", "value": "310.000"},
                        ]
                    }
                ]
            }
        }

        observation = bls_source._extract_observation(payload)

        assert observation is not None
        assert observation.period == date(2025, 3, 1)
        assert observation.value == pytest.approx((312.332 / 303.123 - 1.0) * 100.0)
        assert observation.source == "bls"

    def test_extract_observation_returns_none_for_invalid_schema(self, bls_source: BlsCpiSource):
        assert bls_source._extract_observation({"Results": {"series": []}}) is None


class TestBlsFetchRuntime:
    @pytest.mark.asyncio
    async def test_fetch_us_cpi_yoy_uses_cache(self, bls_source: BlsCpiSource):
        payload = {
            "Results": {
                "series": [
                    {
                        "data": [
                            {"year": "2025", "period": "M03", "value": "110"},
                            {"year": "2024", "period": "M03", "value": "100"},
                        ]
                    }
                ]
            }
        }

        with patch.object(bls_source, "_request_payload", new=AsyncMock(return_value=payload)) as mock_request:
            first = await bls_source.fetch_us_cpi_yoy()
            second = await bls_source.fetch_us_cpi_yoy()

        assert first is not None
        assert second is not None
        assert first.value == pytest.approx(10.0)
        assert second.value == pytest.approx(10.0)
        assert mock_request.await_count == 1

    @pytest.mark.asyncio
    async def test_fetch_us_cpi_yoy_negative_cache_after_empty_payload(self, bls_source: BlsCpiSource):
        with patch.object(bls_source, "_request_payload", new=AsyncMock(return_value=None)) as mock_request:
            first = await bls_source.fetch_us_cpi_yoy()
            second = await bls_source.fetch_us_cpi_yoy()

        assert first is None
        assert second is None
        assert mock_request.await_count == 1

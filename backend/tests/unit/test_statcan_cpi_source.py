"""Tests for Statistics Canada CPI source."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.fundamental_analysis.data_sources.statcan_cpi_source import StatCanCpiSource


@pytest.fixture
def statcan_source():
    return StatCanCpiSource()


class TestStatCanExtractObservation:
    def test_extract_observation_from_json_computes_yoy(self, statcan_source: StatCanCpiSource):
        payload = (
            '{"dataSets":[{"series":{"0:0:0:0:0":{"observations":{"0":[100.0],"1":[103.0]}}}}],'
            '"structure":{"dimensions":{"observation":[{"values":[{"id":"2024-03"},{"id":"2025-03"}]}]}}}'
        )

        observation = statcan_source._extract_observation(payload, "application/json")

        assert observation is not None
        assert observation.period == date(2025, 3, 1)
        assert observation.value == pytest.approx(3.0)
        assert observation.source == "statcan"

    def test_extract_observation_from_csv_computes_yoy(self, statcan_source: StatCanCpiSource):
        payload = "TIME_PERIOD,OBS_VALUE\n2024-03,100\n2025-03,102\n"

        observation = statcan_source._extract_observation(payload, "text/csv")

        assert observation is not None
        assert observation.period == date(2025, 3, 1)
        assert observation.value == pytest.approx(2.0)


class TestStatCanFetchRuntime:
    @pytest.mark.asyncio
    async def test_fetch_ca_cpi_yoy_uses_cache(self, statcan_source: StatCanCpiSource):
        payload = "TIME_PERIOD,OBS_VALUE\n2024-03,100\n2025-03,102\n"

        with patch.object(
            statcan_source,
            "_request_payload",
            new=AsyncMock(return_value=(payload, "text/csv")),
        ) as mock_request:
            first = await statcan_source.fetch_ca_cpi_yoy()
            second = await statcan_source.fetch_ca_cpi_yoy()

        assert first is not None
        assert second is not None
        assert first.value == pytest.approx(2.0)
        assert mock_request.await_count == 1

    @pytest.mark.asyncio
    async def test_fetch_ca_cpi_yoy_negative_cache_after_none_payload(self, statcan_source: StatCanCpiSource):
        with patch.object(statcan_source, "_request_payload", new=AsyncMock(return_value=None)) as mock_request:
            first = await statcan_source.fetch_ca_cpi_yoy()
            second = await statcan_source.fetch_ca_cpi_yoy()

        assert first is None
        assert second is None
        assert mock_request.await_count == 1

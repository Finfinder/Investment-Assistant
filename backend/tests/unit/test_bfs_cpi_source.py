"""Tests for BFS CPI source."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.fundamental_analysis.data_sources.bfs_cpi_source import BfsCpiSource


@pytest.fixture
def bfs_source():
    return BfsCpiSource()


class TestBfsExtractObservation:
    def test_extract_observation_from_csv_uses_latest_month(self, bfs_source: BfsCpiSource):
        payload = "TIME_PERIOD,OBS_VALUE\n2025-03,0.6\n2025-04,0.7\n"

        observation = bfs_source._extract_observation(payload, "text/csv")

        assert observation is not None
        assert observation.period == date(2025, 4, 1)
        assert observation.value == pytest.approx(0.7)
        assert observation.source == "bfs"

    def test_extract_observation_from_json_uses_latest_month(self, bfs_source: BfsCpiSource):
        payload = '[{"period":"2025-03","value":0.6},{"period":"2025-04","value":0.7}]'

        observation = bfs_source._extract_observation(payload, "application/json")

        assert observation is not None
        assert observation.period == date(2025, 4, 1)
        assert observation.value == pytest.approx(0.7)

    def test_extract_observation_ignores_non_finite_values(self, bfs_source: BfsCpiSource):
        payload = "TIME_PERIOD,OBS_VALUE\n2025-03,NaN\n2025-04,inf\n2025-05,0.8\n"

        observation = bfs_source._extract_observation(payload, "text/csv")

        assert observation is not None
        assert observation.period == date(2025, 5, 1)
        assert observation.value == pytest.approx(0.8)


class TestBfsFetchRuntime:
    @pytest.mark.asyncio
    async def test_fetch_ch_cpi_yoy_uses_cache(self, bfs_source: BfsCpiSource):
        payload = "TIME_PERIOD,OBS_VALUE\n2025-04,0.7\n"

        with patch.object(
            bfs_source, "_request_payload", new=AsyncMock(return_value=(payload, "text/csv"))
        ) as mock_request:
            first = await bfs_source.fetch_ch_cpi_yoy()
            second = await bfs_source.fetch_ch_cpi_yoy()

        assert first is not None
        assert second is not None
        assert first.value == pytest.approx(0.7)
        assert mock_request.await_count == 1

    @pytest.mark.asyncio
    async def test_fetch_ch_cpi_yoy_negative_cache_after_empty_payload(self, bfs_source: BfsCpiSource):
        with patch.object(bfs_source, "_request_payload", new=AsyncMock(return_value=None)) as mock_request:
            first = await bfs_source.fetch_ch_cpi_yoy()
            second = await bfs_source.fetch_ch_cpi_yoy()

        assert first is None
        assert second is None
        assert mock_request.await_count == 1

"""Tests for BFS CPI source."""

from datetime import date
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from tenacity import wait_none

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


class TestBfsFetchErrorPaths:
    @pytest.mark.asyncio
    async def test_fetch_ch_cpi_yoy_negative_cache_after_request_exception(self, bfs_source: BfsCpiSource):
        with patch.object(
            bfs_source, "_request_payload", new=AsyncMock(side_effect=RuntimeError("boom"))
        ) as mock_request:
            first = await bfs_source.fetch_ch_cpi_yoy()
            second = await bfs_source.fetch_ch_cpi_yoy()

        assert first is None
        assert second is None
        assert mock_request.await_count == 1

    @pytest.mark.asyncio
    async def test_fetch_ch_cpi_yoy_negative_cache_after_no_observation(self, bfs_source: BfsCpiSource):
        with patch.object(
            bfs_source,
            "_request_payload",
            new=AsyncMock(return_value=("TIME_PERIOD,OBS_VALUE\n", "text/csv")),
        ) as mock_request:
            first = await bfs_source.fetch_ch_cpi_yoy()
            second = await bfs_source.fetch_ch_cpi_yoy()

        assert first is None
        assert second is None
        assert mock_request.await_count == 1


class TestBfsRequest:
    @pytest.fixture(autouse=True)
    def fast_retry(self):
        original_wait = BfsCpiSource._request_payload.retry.wait  # type: ignore[attr-defined]
        BfsCpiSource._request_payload.retry.wait = wait_none()  # type: ignore[attr-defined]
        yield
        BfsCpiSource._request_payload.retry.wait = original_wait  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_request_payload_returns_none_for_4xx(self, bfs_source: BfsCpiSource):
        response = httpx.Response(
            404,
            request=httpx.Request("GET", "https://www.bfs.admin.ch/bfsstatic/dam/assets/36552367/master"),
        )
        with patch("app.modules.fundamental_analysis.data_sources.bfs_cpi_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await bfs_source._request_payload()

        assert result is None
        assert mock_client.get.await_count == 1

    @pytest.mark.asyncio
    async def test_request_payload_retries_on_http_5xx(self, bfs_source: BfsCpiSource):
        first = httpx.Response(
            503,
            request=httpx.Request("GET", "https://www.bfs.admin.ch/bfsstatic/dam/assets/36552367/master"),
        )
        second = httpx.Response(
            200,
            text="TIME_PERIOD,OBS_VALUE\n2025-04,0.7\n",
            headers={"content-type": "text/csv"},
            request=httpx.Request("GET", "https://www.bfs.admin.ch/bfsstatic/dam/assets/36552367/master"),
        )
        with patch("app.modules.fundamental_analysis.data_sources.bfs_cpi_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[first, second])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await bfs_source._request_payload()

        assert result is not None
        assert result[1] == "text/csv"
        assert mock_client.get.await_count == 2

    @pytest.mark.asyncio
    async def test_request_payload_retries_on_transport_error(self, bfs_source: BfsCpiSource):
        second = httpx.Response(
            200,
            text="TIME_PERIOD,OBS_VALUE\n2025-04,0.7\n",
            headers={"content-type": "text/csv"},
            request=httpx.Request("GET", "https://www.bfs.admin.ch/bfsstatic/dam/assets/36552367/master"),
        )
        with patch("app.modules.fundamental_analysis.data_sources.bfs_cpi_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[httpx.ReadTimeout("timeout"), second])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await bfs_source._request_payload()

        assert result is not None
        assert mock_client.get.await_count == 2

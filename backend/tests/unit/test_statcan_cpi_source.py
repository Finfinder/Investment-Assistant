"""Tests for Statistics Canada CPI source."""

from datetime import date
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from tenacity import wait_none

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


class TestStatCanCsvFallback:
    def test_extract_csv_returns_none_for_missing_columns(self, statcan_source: StatCanCpiSource):
        payload = "foo,bar\n2025-03,100\n2025-04,102\n"

        observation = statcan_source._extract_observation(payload, "text/csv")

        assert observation is None

    def test_extract_csv_returns_none_for_header_only(self, statcan_source: StatCanCpiSource):
        payload = "TIME_PERIOD,OBS_VALUE\n"

        observation = statcan_source._extract_observation(payload, "text/csv")

        assert observation is None

    def test_extract_csv_ignores_malformed_value(self, statcan_source: StatCanCpiSource):
        payload = "TIME_PERIOD,OBS_VALUE\n2024-05,100\n2025-04,abc\n2025-05,103\n"

        observation = statcan_source._extract_observation(payload, "text/csv")

        assert observation is not None
        assert observation.period == date(2025, 5, 1)
        assert observation.value == pytest.approx(3.0)


class TestStatCanHelpers:
    def test_decode_json_payload_returns_none_for_invalid_json(self, statcan_source: StatCanCpiSource):
        assert statcan_source._decode_json_payload("not json") is None

    def test_decode_json_payload_returns_none_for_non_dict(self, statcan_source: StatCanCpiSource):
        assert statcan_source._decode_json_payload("[]") is None

    def test_build_period_map_returns_empty_for_missing_structure(self, statcan_source: StatCanCpiSource):
        assert statcan_source._build_period_map({"dataSets": []}) == {}

    def test_build_period_map_returns_empty_for_missing_dimensions(self, statcan_source: StatCanCpiSource):
        assert statcan_source._build_period_map({"structure": {}}) == {}

    def test_build_period_map_returns_empty_for_missing_observation(self, statcan_source: StatCanCpiSource):
        assert statcan_source._build_period_map({"structure": {"dimensions": {}}}) == {}

    def test_build_period_map_returns_empty_for_non_list_values(self, statcan_source: StatCanCpiSource):
        decoded = {"structure": {"dimensions": {"observation": [{"values": "not-a-list"}]}}}
        assert statcan_source._build_period_map(decoded) == {}

    def test_build_period_map_skips_non_dict_items(self, statcan_source: StatCanCpiSource):
        decoded = {"structure": {"dimensions": {"observation": [{"values": ["not-a-dict"]}]}}}
        assert statcan_source._build_period_map(decoded) == {}

    def test_extract_observations_dict_returns_empty_for_missing_datasets(self, statcan_source: StatCanCpiSource):
        assert statcan_source._extract_observations_dict({"structure": {}}) == {}

    def test_extract_observations_dict_returns_empty_for_non_dict_dataset(self, statcan_source: StatCanCpiSource):
        assert statcan_source._extract_observations_dict({"dataSets": ["not-a-dict"]}) == {}

    def test_extract_observations_dict_returns_empty_for_missing_series(self, statcan_source: StatCanCpiSource):
        assert statcan_source._extract_observations_dict({"dataSets": [{}]}) == {}

    def test_extract_observations_dict_returns_empty_for_series_without_observations(
        self, statcan_source: StatCanCpiSource
    ):
        decoded = {"dataSets": [{"series": {"0:0:0:0:0": {"not_observations": {}}}}]}
        assert statcan_source._extract_observations_dict(decoded) == {}

    def test_extract_index_values_from_json_returns_empty_for_no_observations(self, statcan_source: StatCanCpiSource):
        payload = (
            '{"dataSets":[{"series":{"0:0:0:0:0":{"observations":{}}}}],'
            '"structure":{"dimensions":{"observation":[{"values":[{"id":"2025-03"}]}]}}}'
        )
        assert statcan_source._extract_index_values_from_json(payload) == {}

    def test_extract_index_values_from_json_returns_empty_for_period_not_in_map(self, statcan_source: StatCanCpiSource):
        payload = (
            '{"dataSets":[{"series":{"0:0:0:0:0":{"observations":{"0":[100.0]}}}}],'
            '"structure":{"dimensions":{"observation":[{"values":[{"id":"not-a-period"}]}]}}}'
        )
        assert statcan_source._extract_index_values_from_json(payload) == {}


class TestStatCanRequest:
    @pytest.fixture(autouse=True)
    def fast_retry(self):
        original_wait = StatCanCpiSource._request_payload.retry.wait  # type: ignore[attr-defined]
        StatCanCpiSource._request_payload.retry.wait = wait_none()  # type: ignore[attr-defined]
        yield
        StatCanCpiSource._request_payload.retry.wait = original_wait  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_request_payload_returns_none_for_409(self, statcan_source: StatCanCpiSource):
        response = httpx.Response(
            409,
            request=httpx.Request("GET", "https://www150.statcan.gc.ca/t1/wds/sdmx/statcan/rest/vector/v41690973"),
        )
        with patch("app.modules.fundamental_analysis.data_sources.statcan_cpi_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await statcan_source._request_payload()

        assert result is None
        assert mock_client.get.await_count == 1

    @pytest.mark.asyncio
    async def test_fetch_ca_cpi_yoy_negative_cache_after_409(self, statcan_source: StatCanCpiSource):
        response = httpx.Response(
            409,
            request=httpx.Request("GET", "https://www150.statcan.gc.ca/t1/wds/sdmx/statcan/rest/vector/v41690973"),
        )
        with patch("app.modules.fundamental_analysis.data_sources.statcan_cpi_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            first = await statcan_source.fetch_ca_cpi_yoy()
            second = await statcan_source.fetch_ca_cpi_yoy()

        assert first is None
        assert second is None
        assert mock_client.get.await_count == 1

    @pytest.mark.asyncio
    async def test_request_payload_retries_on_http_5xx(self, statcan_source: StatCanCpiSource):
        first = httpx.Response(
            503,
            request=httpx.Request("GET", "https://www150.statcan.gc.ca/t1/wds/sdmx/statcan/rest/vector/v41690973"),
        )
        second = httpx.Response(
            200,
            text="TIME_PERIOD,OBS_VALUE\n2024-03,100\n2025-03,102\n",
            headers={"content-type": "text/csv"},
            request=httpx.Request("GET", "https://www150.statcan.gc.ca/t1/wds/sdmx/statcan/rest/vector/v41690973"),
        )
        with patch("app.modules.fundamental_analysis.data_sources.statcan_cpi_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[first, second])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await statcan_source._request_payload()

        assert result is not None
        assert result[1] == "text/csv"
        assert mock_client.get.await_count == 2

    @pytest.mark.asyncio
    async def test_request_payload_retries_on_transport_error(self, statcan_source: StatCanCpiSource):
        second = httpx.Response(
            200,
            text="TIME_PERIOD,OBS_VALUE\n2024-03,100\n2025-03,102\n",
            headers={"content-type": "text/csv"},
            request=httpx.Request("GET", "https://www150.statcan.gc.ca/t1/wds/sdmx/statcan/rest/vector/v41690973"),
        )
        with patch("app.modules.fundamental_analysis.data_sources.statcan_cpi_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[httpx.ReadTimeout("timeout"), second])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await statcan_source._request_payload()

        assert result is not None
        assert mock_client.get.await_count == 2

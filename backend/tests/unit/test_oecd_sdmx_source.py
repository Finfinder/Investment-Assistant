"""Tests for OECD SDMX source used for JP CPI YoY."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from tenacity import wait_none

from app.modules.fundamental_analysis.data_sources.oecd_sdmx_source import (
    OECD_QUERY_PARAMS,
    OecdSdmxSource,
)


@pytest.fixture
def oecd_source():
    return OecdSdmxSource()


class TestOecdCsvParsing:
    def test_parse_csv_returns_latest_monthly_value(self):
        payload = """REF_AREA,TIME_PERIOD,OBS_VALUE\nJPN,2025-01,2.3\nJPN,2025-03,2.8\nJPN,2025-02,2.5\n"""

        value = OecdSdmxSource._extract_latest_value(payload, "text/csv")

        assert value == pytest.approx(2.8)

    def test_parse_csv_ignores_invalid_values(self):
        payload = """TIME_PERIOD,OBS_VALUE\n2025-01,abc\n2025-02,\n2025-03,1.9\n"""

        value = OecdSdmxSource._extract_latest_value(payload, "text/csv")

        assert value == pytest.approx(1.9)

    def test_parse_csv_ignores_nan_and_inf(self):
        payload = """TIME_PERIOD,OBS_VALUE\n2025-01,NaN\n2025-02,inf\n2025-03,1.1\n"""

        value = OecdSdmxSource._extract_latest_value(payload, "text/csv")

        assert value == pytest.approx(1.1)


class TestOecdJsonParsing:
    def test_parse_json_returns_latest_monthly_value(self):
        payload = (
            '{"dataSets":[{"series":{"0:0:0:0:0:0:0:0":{"observations":'
            '{"0":[1.5],"1":[1.7],"2":[2.0]}}}}],'
            '"structure":{"dimensions":{"observation":[{"values":'
            '[{"id":"2025-01"},{"id":"2025-02"},{"id":"2025-03"}]'
            "}]}}}"
        )

        value = OecdSdmxSource._extract_latest_value(payload, "application/json")

        assert value == pytest.approx(2.0)

    def test_parse_json_returns_none_for_unexpected_schema(self):
        value = OecdSdmxSource._extract_latest_value('{"unexpected":true}', "application/json")

        assert value is None

    def test_parse_json_ignores_nan_and_inf(self):
        payload = (
            '{"dataSets":[{"series":{"0:0:0:0:0:0:0:0":{"observations":'
            '{"0":["NaN"],"1":["inf"],"2":[1.3]}}}}],'
            '"structure":{"dimensions":{"observation":[{"values":'
            '[{"id":"2025-01"},{"id":"2025-02"},{"id":"2025-03"}]'
            "}]}}}"
        )

        value = OecdSdmxSource._extract_latest_value(payload, "application/json")

        assert value == pytest.approx(1.3)

    def test_parse_json_returns_none_for_malformed_json(self):
        value = OecdSdmxSource._extract_latest_value("{not valid json", "application/json")

        assert value is None

    def test_parse_json_returns_none_for_empty_datasets(self):
        value = OecdSdmxSource._extract_latest_value('{"dataSets":[]}', "application/json")

        assert value is None

    def test_parse_json_returns_none_for_missing_structure(self):
        value = OecdSdmxSource._extract_latest_value('{"dataSets":[{}]}', "application/json")

        assert value is None

    def test_parse_json_returns_none_for_empty_period_map(self):
        payload = (
            '{"dataSets":[{"series":{"0:0:0:0:0:0:0:0":{"observations":{"0":[1.3]}}}}],'
            '"structure":{"dimensions":{"observation":[{"values":[{"id":"not-a-period"}]}]}}}'
        )

        value = OecdSdmxSource._extract_latest_value(payload, "application/json")

        assert value is None

    def test_parse_json_returns_none_for_empty_observations(self):
        payload = (
            '{"dataSets":[{"series":{"0:0:0:0:0:0:0:0":{}}}],'
            '"structure":{"dimensions":{"observation":[{"values":[{"id":"2025-03"}]}]}}}'
        )

        value = OecdSdmxSource._extract_latest_value(payload, "application/json")

        assert value is None

    def test_extract_latest_value_falls_back_to_csv_for_plain_text(self):
        payload = "TIME_PERIOD,OBS_VALUE\n2025-01,2.3\n2025-03,2.8\n2025-02,2.5\n"

        value = OecdSdmxSource._extract_latest_value(payload, "text/plain")

        assert value == pytest.approx(2.8)


class TestOecdFetchRuntime:
    @pytest.mark.asyncio
    async def test_fetch_jp_cpi_yoy_uses_cache_after_first_request(self, oecd_source: OecdSdmxSource):
        payload = "TIME_PERIOD,OBS_VALUE\n2025-03,2.8\n"

        with patch.object(
            oecd_source,
            "_request_payload",
            new=AsyncMock(return_value=(payload, "text/csv")),
        ) as mock_request:
            first = await oecd_source.fetch_jp_cpi_yoy()
            second = await oecd_source.fetch_jp_cpi_yoy()

        assert first == pytest.approx(2.8)
        assert second == pytest.approx(2.8)
        assert mock_request.await_count == 1

    @pytest.mark.asyncio
    async def test_fetch_jp_cpi_yoy_returns_none_and_negative_caches_on_empty_payload(
        self, oecd_source: OecdSdmxSource
    ):
        with patch.object(
            oecd_source,
            "_request_payload",
            new=AsyncMock(return_value=("TIME_PERIOD,OBS_VALUE\n", "text/csv")),
        ) as mock_request:
            first = await oecd_source.fetch_jp_cpi_yoy()
            second = await oecd_source.fetch_jp_cpi_yoy()

        assert first is None
        assert second is None
        assert mock_request.await_count == 1

    @pytest.mark.asyncio
    async def test_fetch_jp_cpi_yoy_zero_value_is_valid(self, oecd_source: OecdSdmxSource):
        with patch.object(
            oecd_source,
            "_request_payload",
            new=AsyncMock(return_value=("TIME_PERIOD,OBS_VALUE\n2025-03,0.0\n", "text/csv")),
        ):
            result = await oecd_source.fetch_jp_cpi_yoy()

        assert result == pytest.approx(0.0)


class TestOecdRequest:
    @pytest.fixture(autouse=True)
    def fast_retry(self):
        original_wait = OecdSdmxSource._request_payload.retry.wait  # type: ignore[attr-defined]
        OecdSdmxSource._request_payload.retry.wait = wait_none()  # type: ignore[attr-defined]
        yield
        OecdSdmxSource._request_payload.retry.wait = original_wait  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_request_payload_uses_expected_query_params(self, oecd_source: OecdSdmxSource):
        response = httpx.Response(
            200,
            text="TIME_PERIOD,OBS_VALUE\n2025-03,2.8\n",
            headers={"content-type": "text/csv"},
            request=httpx.Request("GET", "https://sdmx.oecd.org/public/rest/v1/data"),
        )

        with patch("app.modules.fundamental_analysis.data_sources.oecd_sdmx_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            payload = await oecd_source._request_payload()

        assert payload is not None
        assert payload[1] == "text/csv"

        call = mock_client.get.call_args
        params = call.kwargs.get("params", call[1].get("params", {}))
        assert params["c[REF_AREA]"] == "JPN"
        assert params["c[MEASURE]"] == "CPI"
        assert params["c[FREQ]"] == "M"
        assert params["c[TRANSFORMATION]"] == "GY"
        assert params["format"] == "sdmx-json"

        for key, expected in OECD_QUERY_PARAMS.items():
            assert params[key] == expected

    @pytest.mark.asyncio
    async def test_request_payload_returns_none_for_404(self, oecd_source: OecdSdmxSource):
        response = httpx.Response(
            404,
            request=httpx.Request("GET", "https://sdmx.oecd.org/public/rest/v1/data"),
        )

        with patch("app.modules.fundamental_analysis.data_sources.oecd_sdmx_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await oecd_source._request_payload()

        assert result is None
        assert mock_client.get.await_count == 1

    @pytest.mark.asyncio
    async def test_request_payload_retries_on_http_5xx(self, oecd_source: OecdSdmxSource):
        first = httpx.Response(
            503,
            request=httpx.Request("GET", "https://sdmx.oecd.org/public/rest/v1/data"),
        )
        second = httpx.Response(
            200,
            text="TIME_PERIOD,OBS_VALUE\n2025-03,2.8\n",
            headers={"content-type": "text/csv"},
            request=httpx.Request("GET", "https://sdmx.oecd.org/public/rest/v1/data"),
        )

        with patch("app.modules.fundamental_analysis.data_sources.oecd_sdmx_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[first, second])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await oecd_source._request_payload()

        assert result is not None
        assert result[1] == "text/csv"
        assert mock_client.get.await_count == 2

    @pytest.mark.asyncio
    async def test_request_payload_retries_on_transport_error(self, oecd_source: OecdSdmxSource):
        second = httpx.Response(
            200,
            text="TIME_PERIOD,OBS_VALUE\n2025-03,2.8\n",
            headers={"content-type": "text/csv"},
            request=httpx.Request("GET", "https://sdmx.oecd.org/public/rest/v1/data"),
        )

        with patch("app.modules.fundamental_analysis.data_sources.oecd_sdmx_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[httpx.ReadTimeout("timeout"), second])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await oecd_source._request_payload()

        assert result is not None
        assert mock_client.get.await_count == 2

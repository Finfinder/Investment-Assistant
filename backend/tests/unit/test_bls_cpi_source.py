"""Tests for BLS CPI source."""

from datetime import date
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from tenacity import wait_none

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


class TestBlsRequest:
    @pytest.fixture(autouse=True)
    def fast_retry(self):
        original_wait = BlsCpiSource._request_payload.retry.wait  # type: ignore[attr-defined]
        BlsCpiSource._request_payload.retry.wait = wait_none()  # type: ignore[attr-defined]
        yield
        BlsCpiSource._request_payload.retry.wait = original_wait  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_request_payload_returns_none_for_invalid_json(self, bls_source: BlsCpiSource):
        response = httpx.Response(
            200,
            text="not json",
            request=httpx.Request("POST", "https://api.bls.gov/publicAPI/v2/timeseries/data/"),
        )
        with patch("app.modules.fundamental_analysis.data_sources.bls_cpi_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await bls_source._request_payload()

        assert result is None
        assert mock_client.post.await_count == 1

    @pytest.mark.asyncio
    async def test_request_payload_returns_none_for_non_dict_json(self, bls_source: BlsCpiSource):
        response = httpx.Response(
            200,
            text="[]",
            request=httpx.Request("POST", "https://api.bls.gov/publicAPI/v2/timeseries/data/"),
        )
        with patch("app.modules.fundamental_analysis.data_sources.bls_cpi_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await bls_source._request_payload()

        assert result is None
        assert mock_client.post.await_count == 1

    @pytest.mark.asyncio
    async def test_request_payload_returns_none_for_4xx(self, bls_source: BlsCpiSource):
        response = httpx.Response(
            404,
            request=httpx.Request("POST", "https://api.bls.gov/publicAPI/v2/timeseries/data/"),
        )
        with patch("app.modules.fundamental_analysis.data_sources.bls_cpi_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await bls_source._request_payload()

        assert result is None
        assert mock_client.post.await_count == 1

    @pytest.mark.asyncio
    async def test_request_payload_retries_on_http_5xx(self, bls_source: BlsCpiSource):
        first = httpx.Response(
            503,
            request=httpx.Request("POST", "https://api.bls.gov/publicAPI/v2/timeseries/data/"),
        )
        second = httpx.Response(
            200,
            text='{"Results":{"series":[{"data":[{"year":"2025","period":"M03","value":"110"},{"year":"2024","period":"M03","value":"100"}]}]}}',
            request=httpx.Request("POST", "https://api.bls.gov/publicAPI/v2/timeseries/data/"),
        )
        with patch("app.modules.fundamental_analysis.data_sources.bls_cpi_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=[first, second])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await bls_source._request_payload()

        assert result is not None
        assert mock_client.post.await_count == 2

    @pytest.mark.asyncio
    async def test_request_payload_retries_on_transport_error(self, bls_source: BlsCpiSource):
        second = httpx.Response(
            200,
            text='{"Results":{"series":[{"data":[{"year":"2025","period":"M03","value":"110"},{"year":"2024","period":"M03","value":"100"}]}]}}',
            request=httpx.Request("POST", "https://api.bls.gov/publicAPI/v2/timeseries/data/"),
        )
        with patch("app.modules.fundamental_analysis.data_sources.bls_cpi_source.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=[httpx.ReadTimeout("timeout"), second])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await bls_source._request_payload()

        assert result is not None
        assert mock_client.post.await_count == 2

"""Statistics Canada source dla CPI YoY."""

import logging
from typing import Any

import httpx
from cachetools import TTLCache
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .cpi_yoy import compute_yoy_observation, parse_monthly_period
from .macro_observation import MacroObservation

logger = logging.getLogger(__name__)

STATCAN_VECTOR_ID = "v41690973"
STATCAN_URL = f"https://www150.statcan.gc.ca/t1/wds/sdmx/statcan/rest/vector/{STATCAN_VECTOR_ID}?lastNObservations=16"

HTTP_TIMEOUT = httpx.Timeout(20.0, connect=5.0)
MAX_RETRIES = 3
RETRY_MIN_WAIT_SECONDS = 1
RETRY_MAX_WAIT_SECONDS = 8

CACHE_TTL_SECONDS = 86400
CACHE_MAX_SIZE = 16
NEGATIVE_CACHE_TTL_SECONDS = 300
NEGATIVE_CACHE_MAX_SIZE = 16

_NEGATIVE_CACHE_SENTINEL = object()


class StatCanTransientHttpError(RuntimeError):
    """Raised for transient StatCan statuses that should be retried."""


class StatCanCpiSource:
    """Fetches Canada CPI YoY from StatCan vector API."""

    def __init__(self) -> None:
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL_SECONDS)
        self._negative_cache: TTLCache[str, object] = TTLCache(
            maxsize=NEGATIVE_CACHE_MAX_SIZE,
            ttl=NEGATIVE_CACHE_TTL_SECONDS,
        )

    @staticmethod
    def _decode_json_payload(payload: str) -> dict[str, Any] | None:
        try:
            decoded = httpx.Response(200, text=payload).json()
        except ValueError:
            return None
        if not isinstance(decoded, dict):
            return None
        return decoded

    @staticmethod
    def _build_period_map(decoded: dict[str, Any]) -> dict[int, Any]:
        structure = decoded.get("structure")
        if not isinstance(structure, dict):
            return {}

        dimensions = structure.get("dimensions")
        if not isinstance(dimensions, dict):
            return {}

        observation_dimensions = dimensions.get("observation")
        if not isinstance(observation_dimensions, list) or not observation_dimensions:
            return {}

        values = observation_dimensions[0].get("values")
        if not isinstance(values, list):
            return {}

        period_map: dict[int, Any] = {}
        for idx, item in enumerate(values):
            if not isinstance(item, dict):
                continue
            period_text = str(item.get("id") or item.get("name") or "").strip()
            parsed = parse_monthly_period(period_text)
            if parsed is not None:
                period_map[idx] = parsed

        return period_map

    @staticmethod
    def _extract_observations_dict(decoded: dict[str, Any]) -> dict[str, Any]:
        data_sets = decoded.get("dataSets")
        if not isinstance(data_sets, list) or not data_sets:
            return {}

        first_data_set = data_sets[0]
        if not isinstance(first_data_set, dict):
            return {}

        series = first_data_set.get("series")
        if not isinstance(series, dict):
            return {}

        for series_value in series.values():
            if not isinstance(series_value, dict):
                continue
            obs = series_value.get("observations")
            if isinstance(obs, dict):
                return obs

        return {}

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT_SECONDS, max=RETRY_MAX_WAIT_SECONDS),
        retry=retry_if_exception_type((OSError, httpx.RequestError, httpx.TimeoutException, StatCanTransientHttpError)),
        reraise=True,
    )
    async def _request_payload(self) -> tuple[str, str] | None:
        headers = {
            "Accept": "application/vnd.sdmx.data+json;version=1.0.0, application/json, text/csv",
        }

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(STATCAN_URL, headers=headers)

        if response.status_code == 409:
            logger.warning("StatCan: temporary refresh window (409)")
            return None

        if response.status_code >= 500:
            raise StatCanTransientHttpError(f"StatCan transient HTTP {response.status_code}")

        if response.status_code >= 400:
            logger.warning("StatCan: non-retryable HTTP status=%d", response.status_code)
            return None

        return response.text, response.headers.get("content-type", "")

    @staticmethod
    def _extract_index_values_from_json(payload: str) -> dict[Any, float]:
        decoded = StatCanCpiSource._decode_json_payload(payload)
        if decoded is None:
            return {}
        period_map = StatCanCpiSource._build_period_map(decoded)
        observations = StatCanCpiSource._extract_observations_dict(decoded)
        if not observations:
            return {}

        index_values: dict[Any, float] = {}
        for obs_index, obs_value in observations.items():
            try:
                idx = int(str(obs_index).split(":", maxsplit=1)[0])
            except ValueError:
                continue

            period = period_map.get(idx)
            if period is None:
                continue

            if not isinstance(obs_value, list) or not obs_value:
                continue

            try:
                value = float(obs_value[0])
            except (TypeError, ValueError):
                continue

            index_values[period] = value

        return index_values

    @staticmethod
    def _extract_index_values_from_csv(payload: str) -> dict[Any, float]:
        index_values: dict[Any, float] = {}
        lines = [line.strip() for line in payload.splitlines() if line.strip()]
        if len(lines) < 2:
            return index_values

        header = [part.strip() for part in lines[0].split(",")]
        try:
            period_idx = header.index("TIME_PERIOD")
            value_idx = header.index("OBS_VALUE")
        except ValueError:
            return index_values

        for line in lines[1:]:
            parts = [part.strip() for part in line.split(",")]
            if len(parts) <= max(period_idx, value_idx):
                continue

            period = parse_monthly_period(parts[period_idx])
            if period is None:
                continue

            try:
                value = float(parts[value_idx])
            except ValueError:
                continue

            index_values[period] = value

        return index_values

    @classmethod
    def _extract_observation(cls, payload: str, content_type: str) -> MacroObservation | None:
        if "csv" in content_type.lower():
            index_values = cls._extract_index_values_from_csv(payload)
        else:
            index_values = cls._extract_index_values_from_json(payload)

        return compute_yoy_observation(index_values, source="statcan")

    async def fetch_ca_cpi_yoy(self) -> MacroObservation | None:
        cache_key = "statcan:ca_cpi_yoy"

        cached = self._cache.get(cache_key)
        if isinstance(cached, MacroObservation):
            return cached

        if cache_key in self._negative_cache:
            return None

        try:
            payload_result = await self._request_payload()
        except Exception as exc:
            logger.warning("StatCan: failed to fetch CA CPI: %s", exc)
            self._negative_cache[cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        if payload_result is None:
            self._negative_cache[cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        payload, content_type = payload_result
        observation = self._extract_observation(payload, content_type)
        if observation is None:
            logger.warning("StatCan: no usable CPI observation")
            self._negative_cache[cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        self._cache[cache_key] = observation
        self._negative_cache.pop(cache_key, None)
        logger.info("StatCan: CA CPI YoY = %.4f (%s)", observation.value, observation.period)
        return observation

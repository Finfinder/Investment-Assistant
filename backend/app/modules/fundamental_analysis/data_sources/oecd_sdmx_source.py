"""OECD SDMX REST integration for Japan monthly CPI YoY."""

import csv
import io
import logging
import math
import re
from datetime import datetime
from typing import Any

import httpx
from cachetools import TTLCache
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

OECD_BASE_URL = "https://sdmx.oecd.org/public/rest/v1"
OECD_DATA_ENDPOINT = "/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/all"

OECD_QUERY_PARAMS: dict[str, str] = {
    "c[REF_AREA]": "JPN",
    "c[MEASURE]": "CPI",
    "c[UNIT_MEASURE]": "PAM",
    "c[METHODOLOGY]": "N",
    "c[EXPENDITURE]": "_T",
    "c[ADJUSTMENT]": "N",
    "c[TRANSFORMATION]": "GY",
    "c[FREQ]": "M",
    "format": "sdmx-json",
}

HTTP_TIMEOUT = httpx.Timeout(20.0, connect=5.0)
MAX_RETRIES = 3
RETRY_MIN_WAIT_SECONDS = 1
RETRY_MAX_WAIT_SECONDS = 8

CACHE_TTL_SECONDS = 86400
CACHE_MAX_SIZE = 16
NEGATIVE_CACHE_TTL_SECONDS = 300
NEGATIVE_CACHE_MAX_SIZE = 16

_MONTHLY_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_NEGATIVE_CACHE_SENTINEL = object()


class OecdTransientHttpError(RuntimeError):
    """Raised for transient HTTP statuses that should be retried."""


class OecdSdmxSource:
    """Fetches monthly CPI YoY for Japan from OECD SDMX REST."""

    def __init__(self) -> None:
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL_SECONDS)
        self._negative_cache: TTLCache[str, object] = TTLCache(
            maxsize=NEGATIVE_CACHE_MAX_SIZE,
            ttl=NEGATIVE_CACHE_TTL_SECONDS,
        )

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT_SECONDS, max=RETRY_MAX_WAIT_SECONDS),
        retry=retry_if_exception_type((OSError, httpx.RequestError, httpx.TimeoutException, OecdTransientHttpError)),
        reraise=True,
    )
    async def _request_payload(self) -> tuple[str, str] | None:
        url = f"{OECD_BASE_URL}{OECD_DATA_ENDPOINT}"
        headers = {
            "Accept": "application/vnd.sdmx.data+json;version=1.0.0, application/json, text/csv",
        }

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(url, params=OECD_QUERY_PARAMS, headers=headers)

        if response.status_code >= 500:
            raise OecdTransientHttpError(f"OECD transient HTTP {response.status_code}")

        if response.status_code >= 400:
            logger.warning("OECD: non-retryable HTTP status=%d for JP CPI", response.status_code)
            return None

        content_type = response.headers.get("content-type", "")
        return response.text, content_type

    @staticmethod
    def _parse_period_to_key(period: str) -> datetime | None:
        if _MONTHLY_PERIOD_RE.match(period) is None:
            return None
        try:
            return datetime.strptime(period, "%Y-%m")
        except ValueError:
            return None

    @staticmethod
    def _parse_csv_payload(payload: str) -> float | None:
        reader = csv.DictReader(io.StringIO(payload))
        latest_period = ""
        latest_value: float | None = None

        for row in reader:
            period = (
                row.get("TIME_PERIOD") or row.get("TIME") or row.get("time_period") or row.get("Time Period") or ""
            ).strip()
            value_raw = (
                row.get("OBS_VALUE")
                or row.get("OBS")
                or row.get("obs_value")
                or row.get("Value")
                or row.get("value")
                or ""
            ).strip()

            if OecdSdmxSource._parse_period_to_key(period) is None:
                continue

            try:
                value = float(value_raw)
            except ValueError:
                continue

            if not math.isfinite(value):
                continue

            if period > latest_period:
                latest_period = period
                latest_value = value

        return latest_value

    @staticmethod
    def _parse_sdmx_json_payload(payload: str) -> float | None:
        try:
            decoded = httpx.Response(200, text=payload).json()
        except ValueError:
            return None

        if not isinstance(decoded, dict):
            return None

        data_sets = decoded.get("dataSets")
        structure = decoded.get("structure")
        if not isinstance(data_sets, list) or not data_sets:
            return None
        if not isinstance(structure, dict):
            return None

        dimensions = structure.get("dimensions")
        if not isinstance(dimensions, dict):
            return None

        observation_dimensions = dimensions.get("observation")
        if not isinstance(observation_dimensions, list) or not observation_dimensions:
            return None

        values = observation_dimensions[0].get("values")
        if not isinstance(values, list):
            return None

        period_map: dict[int, str] = {}
        for idx, item in enumerate(values):
            if not isinstance(item, dict):
                continue
            period = str(item.get("id") or item.get("name") or "").strip()
            if OecdSdmxSource._parse_period_to_key(period) is not None:
                period_map[idx] = period

        if not period_map:
            return None

        first_data_set = data_sets[0]
        if not isinstance(first_data_set, dict):
            return None

        series = first_data_set.get("series")
        if not isinstance(series, dict):
            return None

        observations: dict[str, Any] = {}
        for series_value in series.values():
            if not isinstance(series_value, dict):
                continue
            obs = series_value.get("observations")
            if isinstance(obs, dict):
                observations = obs
                break

        if not observations:
            return None

        latest_period = ""
        latest_value: float | None = None
        for obs_index, obs_value in observations.items():
            try:
                idx = int(str(obs_index).split(":", maxsplit=1)[0])
            except ValueError:
                continue

            period_label = period_map.get(idx)
            if period_label is None:
                continue

            if not isinstance(obs_value, list) or not obs_value:
                continue

            try:
                value = float(obs_value[0])
            except (TypeError, ValueError):
                continue

            if not math.isfinite(value):
                continue

            if period_label > latest_period:
                latest_period = period_label
                latest_value = value

        return latest_value

    @staticmethod
    def _extract_latest_value(payload: str, content_type: str) -> float | None:
        content_type_lower = content_type.lower()

        if "csv" in content_type_lower:
            return OecdSdmxSource._parse_csv_payload(payload)

        payload_stripped = payload.lstrip()
        if payload_stripped.startswith("{"):
            return OecdSdmxSource._parse_sdmx_json_payload(payload)

        # Defensive fallback for gateways that return CSV without content-type.
        return OecdSdmxSource._parse_csv_payload(payload)

    async def fetch_jp_cpi_yoy(self) -> float | None:
        cache_key = "oecd:jp_cpi_yoy"

        cached = self._cache.get(cache_key)
        if cached is not None:
            return float(cached)

        if cache_key in self._negative_cache:
            return None

        try:
            payload_result = await self._request_payload()
        except Exception as exc:
            logger.warning("OECD: failed to fetch JP CPI YoY: %s", exc)
            self._negative_cache[cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        if payload_result is None:
            self._negative_cache[cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        payload, content_type = payload_result
        value = self._extract_latest_value(payload, content_type)
        if value is None:
            logger.warning("OECD: no JP CPI YoY value found in response")
            self._negative_cache[cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        self._cache[cache_key] = value
        self._negative_cache.pop(cache_key, None)
        logger.info("OECD: JP CPI YoY = %.4f", value)
        return value

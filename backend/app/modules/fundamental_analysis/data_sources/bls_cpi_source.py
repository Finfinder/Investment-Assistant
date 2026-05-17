"""BLS API source dla US CPI YoY."""

import logging
from datetime import UTC, date, datetime
from typing import Any

import httpx
from cachetools import TTLCache
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .cpi_yoy import compute_yoy_observation, parse_bls_period
from .macro_observation import MacroObservation

logger = logging.getLogger(__name__)

BLS_BASE_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_SERIES_ID = "CUUR0000SA0"
BLS_LATEST_YEARS_SPAN = 3

HTTP_TIMEOUT = httpx.Timeout(20.0, connect=5.0)
MAX_RETRIES = 3
RETRY_MIN_WAIT_SECONDS = 1
RETRY_MAX_WAIT_SECONDS = 8

CACHE_TTL_SECONDS = 86400
CACHE_MAX_SIZE = 16
NEGATIVE_CACHE_TTL_SECONDS = 300
NEGATIVE_CACHE_MAX_SIZE = 16

_NEGATIVE_CACHE_SENTINEL = object()


class BlsTransientHttpError(RuntimeError):
    """Raised for transient BLS statuses that should be retried."""


class BlsCpiSource:
    """Fetches US CPI YoY from BLS index series."""

    def __init__(self) -> None:
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL_SECONDS)
        self._negative_cache: TTLCache[str, object] = TTLCache(
            maxsize=NEGATIVE_CACHE_MAX_SIZE,
            ttl=NEGATIVE_CACHE_TTL_SECONDS,
        )

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT_SECONDS, max=RETRY_MAX_WAIT_SECONDS),
        retry=retry_if_exception_type((OSError, httpx.RequestError, httpx.TimeoutException, BlsTransientHttpError)),
        reraise=True,
    )
    async def _request_payload(self) -> dict[str, Any] | None:
        year_now = datetime.now(UTC).year
        payload = {
            "seriesid": [BLS_SERIES_ID],
            "startyear": str(year_now - BLS_LATEST_YEARS_SPAN),
            "endyear": str(year_now),
        }

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(BLS_BASE_URL, json=payload)

        if response.status_code >= 500:
            raise BlsTransientHttpError(f"BLS transient HTTP {response.status_code}")

        if response.status_code >= 400:
            logger.warning("BLS: non-retryable HTTP status=%d", response.status_code)
            return None

        try:
            decoded = response.json()
        except ValueError:
            logger.warning("BLS: invalid JSON payload")
            return None

        if not isinstance(decoded, dict):
            return None

        return decoded

    @staticmethod
    def _extract_observation(payload: dict[str, Any]) -> MacroObservation | None:
        results = payload.get("Results")
        if not isinstance(results, dict):
            return None

        series_list = results.get("series")
        if not isinstance(series_list, list) or not series_list:
            return None

        first_series = series_list[0]
        if not isinstance(first_series, dict):
            return None

        data = first_series.get("data")
        if not isinstance(data, list):
            return None

        index_values: dict[date, float] = {}
        for item in data:
            if not isinstance(item, dict):
                continue

            year = str(item.get("year") or "").strip()
            period = str(item.get("period") or "").strip()
            period_date = parse_bls_period(year, period)
            if period_date is None:
                continue

            try:
                value = float(str(item.get("value") or "").replace(",", ""))
            except ValueError:
                continue

            index_values[period_date] = value

        return compute_yoy_observation(index_values, source="bls")

    async def fetch_us_cpi_yoy(self) -> MacroObservation | None:
        cache_key = "bls:us_cpi_yoy"

        cached = self._cache.get(cache_key)
        if isinstance(cached, MacroObservation):
            return cached

        if cache_key in self._negative_cache:
            return None

        try:
            payload = await self._request_payload()
        except Exception as exc:
            logger.warning("BLS: failed to fetch US CPI: %s", exc)
            self._negative_cache[cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        if payload is None:
            self._negative_cache[cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        observation = self._extract_observation(payload)
        if observation is None:
            logger.warning("BLS: no usable CPI observation")
            self._negative_cache[cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        self._cache[cache_key] = observation
        self._negative_cache.pop(cache_key, None)
        logger.info("BLS: US CPI YoY = %.4f (%s)", observation.value, observation.period)
        return observation

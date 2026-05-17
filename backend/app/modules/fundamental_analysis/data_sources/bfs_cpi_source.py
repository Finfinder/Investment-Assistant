"""BFS/FSO source dla szwajcarskiego CPI YoY."""

import csv
import io
import logging
import math
from datetime import date
from typing import Any

import httpx
from cachetools import TTLCache
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .cpi_yoy import parse_monthly_period
from .macro_observation import MacroObservation

logger = logging.getLogger(__name__)

# Kod serii BFS: "gd-q-05.02-yyc" (dokumentacyjnie)
BFS_CPI_YOY_CSV_URL = "https://www.bfs.admin.ch/bfsstatic/dam/assets/36552367/master"

HTTP_TIMEOUT = httpx.Timeout(20.0, connect=5.0)
MAX_RETRIES = 3
RETRY_MIN_WAIT_SECONDS = 1
RETRY_MAX_WAIT_SECONDS = 8

CACHE_TTL_SECONDS = 86400
CACHE_MAX_SIZE = 16
NEGATIVE_CACHE_TTL_SECONDS = 300
NEGATIVE_CACHE_MAX_SIZE = 16

_NEGATIVE_CACHE_SENTINEL = object()


class BfsTransientHttpError(RuntimeError):
    """Raised for transient BFS statuses that should be retried."""


class BfsCpiSource:
    """Fetches Swiss CPI YoY from BFS official dataset endpoint."""

    def __init__(self) -> None:
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL_SECONDS)
        self._negative_cache: TTLCache[str, object] = TTLCache(
            maxsize=NEGATIVE_CACHE_MAX_SIZE,
            ttl=NEGATIVE_CACHE_TTL_SECONDS,
        )

    @staticmethod
    def _decode_json_payload(payload: str) -> list[dict[str, Any]]:
        try:
            decoded = httpx.Response(200, text=payload).json()
        except ValueError:
            return []

        if not isinstance(decoded, list):
            return []

        return [item for item in decoded if isinstance(item, dict)]

    @staticmethod
    def _extract_latest_from_points(points: list[dict[str, Any]]) -> MacroObservation | None:
        def parse_point(item: dict[str, Any]) -> tuple[date, float] | None:
            period = parse_monthly_period(str(item.get("period") or item.get("TIME_PERIOD") or ""))
            if period is None:
                return None
            raw_value = item.get("value") or item.get("OBS_VALUE")
            if raw_value is None:
                return None
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                return None
            if not math.isfinite(value):
                return None
            return (period, value)

        valid_points: list[tuple[date, float]] = [p for p in (parse_point(item) for item in points) if p is not None]
        if not valid_points:
            return None
        latest_period, latest_value = max(valid_points, key=lambda x: x[0])
        return MacroObservation(
            value=latest_value,
            period=latest_period,
            source="bfs",
            unit="pct_yoy",
        )

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT_SECONDS, max=RETRY_MAX_WAIT_SECONDS),
        retry=retry_if_exception_type((OSError, httpx.RequestError, httpx.TimeoutException, BfsTransientHttpError)),
        reraise=True,
    )
    async def _request_payload(self) -> tuple[str, str] | None:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(BFS_CPI_YOY_CSV_URL)

        if response.status_code >= 500:
            raise BfsTransientHttpError(f"BFS transient HTTP {response.status_code}")

        if response.status_code >= 400:
            logger.warning("BFS: non-retryable HTTP status=%d", response.status_code)
            return None

        return response.text, response.headers.get("content-type", "")

    @staticmethod
    def _extract_observation_from_csv(payload: str) -> MacroObservation | None:
        reader = csv.DictReader(io.StringIO(payload))
        latest_period = None
        latest_value: float | None = None

        for row in reader:
            period_text = row.get("TIME_PERIOD") or row.get("TIME") or row.get("Period") or row.get("period") or ""
            value_text = row.get("OBS_VALUE") or row.get("Value") or row.get("value") or row.get("inflation_yoy") or ""

            period = parse_monthly_period(period_text)
            if period is None:
                continue

            try:
                value = float(value_text)
            except ValueError:
                continue

            if not math.isfinite(value):
                continue

            if latest_period is None or period > latest_period:
                latest_period = period
                latest_value = value

        if latest_period is None or latest_value is None:
            return None

        return MacroObservation(
            value=latest_value,
            period=latest_period,
            source="bfs",
            unit="pct_yoy",
        )

    @staticmethod
    def _extract_observation_from_json(payload: str) -> MacroObservation | None:
        points = BfsCpiSource._decode_json_payload(payload)
        return BfsCpiSource._extract_latest_from_points(points)

    @classmethod
    def _extract_observation(cls, payload: str, content_type: str) -> MacroObservation | None:
        content_lower = content_type.lower()
        if "json" in content_lower:
            return cls._extract_observation_from_json(payload)
        return cls._extract_observation_from_csv(payload)

    async def fetch_ch_cpi_yoy(self) -> MacroObservation | None:
        cache_key = "bfs:ch_cpi_yoy"

        cached = self._cache.get(cache_key)
        if isinstance(cached, MacroObservation):
            return cached

        if cache_key in self._negative_cache:
            return None

        try:
            payload_result = await self._request_payload()
        except Exception as exc:
            logger.warning("BFS: failed to fetch CH CPI: %s", exc)
            self._negative_cache[cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        if payload_result is None:
            self._negative_cache[cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        payload, content_type = payload_result
        observation = self._extract_observation(payload, content_type)
        if observation is None:
            logger.warning("BFS: no usable CPI observation")
            self._negative_cache[cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        self._cache[cache_key] = observation
        self._negative_cache.pop(cache_key, None)
        logger.info("BFS: CH CPI YoY = %.4f (%s)", observation.value, observation.period)
        return observation

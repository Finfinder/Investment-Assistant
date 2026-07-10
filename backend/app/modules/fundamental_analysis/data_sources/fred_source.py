"""FRED API integration for macroeconomic data."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from cachetools import TTLCache
from tenacity import RetryCallState, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging_config import sanitize_log_message

from .macro_observation import MacroObservation

logger = logging.getLogger(__name__)

DEFAULT_LOOKBACK_DAYS = 365
QUARTERLY_LOOKBACK_DAYS = 540
SEMIANNUAL_LOOKBACK_DAYS = 540
ANNUAL_LOOKBACK_DAYS = 730
YOY_UNITS_MIN_LOOKBACK_DAYS = 540

FREQUENCY_LOOKBACK_DAYS: dict[str, int] = {
    "D": DEFAULT_LOOKBACK_DAYS,
    "W": DEFAULT_LOOKBACK_DAYS,
    "WEF": DEFAULT_LOOKBACK_DAYS,
    "WETH": DEFAULT_LOOKBACK_DAYS,
    "WEW": DEFAULT_LOOKBACK_DAYS,
    "WETU": DEFAULT_LOOKBACK_DAYS,
    "WEM": DEFAULT_LOOKBACK_DAYS,
    "WESU": DEFAULT_LOOKBACK_DAYS,
    "WESA": DEFAULT_LOOKBACK_DAYS,
    "BW": DEFAULT_LOOKBACK_DAYS,
    "BWEW": DEFAULT_LOOKBACK_DAYS,
    "BWEM": DEFAULT_LOOKBACK_DAYS,
    "M": DEFAULT_LOOKBACK_DAYS,
    "Q": QUARTERLY_LOOKBACK_DAYS,
    "SA": SEMIANNUAL_LOOKBACK_DAYS,
    "A": ANNUAL_LOOKBACK_DAYS,
}

# FRED series identifiers for key macro indicators
FRED_SERIES: dict[str, str] = {
    "fed_funds_rate": "FEDFUNDS",
    "cpi_us": "CPALTT01USM659N",
    "nonfarm_payrolls": "PAYEMS",
    "ism_pmi": "MANEMP",
    "gdp_us": "GDP",
    "unemployment_us": "UNRATE",
    "treasury_10y": "DGS10",
    "treasury_2y": "DGS2",
    "ecb_rate": "ECBDFR",
    "cpi_eu": "CP0000EZ19M086NEST",
    "cpi_uk": "CPALTT01GBM659N",
    "cpi_ch": "CPALTT01CHM659N",
    "cpi_au": "CPALTT01AUQ659N",  # Quarterly, OECD — ABS publishes CPI quarterly, no monthly series on FRED
    "cpi_ca": "CPALTT01CAM659N",
    "boj_rate": "IRSTCI01JPM156N",
    "boe_rate": "IUDSOIA",
    "rba_rate": "IRSTCI01AUM156N",
    "boc_rate": "IRSTCI01CAM156N",
    "pl_rate": "IR3TIB01PLM156N",
    "cpi_pl": "CPALTT01PLM659N",
    "unemployment_pl": "LRHUTTTTPLM156S",
    "gdp_pl": "CLVMNACSCAB1GQPL",
    # IRSTCI01CHM156N (overnight rate) discontinued Apr 2024 — replaced by 3-month interbank rate (OECD MEI)
    "snb_rate": "IR3TIB01CHM156N",
    # IRSTCI01NZM156N (overnight rate) discontinued Jan 2025 — replaced by 3-month interbank rate (OECD MEI)
    "rbnz_rate": "IR3TIB01NZM156N",
    "cpi_nz": "NZLCPIALLQINMEI",  # Quarterly Index 2015=100, OECD — Stats NZ publishes CPI quarterly; needs units=pc1
}

# Fallback FRED series used only after the primary indicator series returns no data.
FRED_SERIES_FALLBACKS: dict[str, tuple[str, ...]] = {
    "cpi_au": ("FPCPITOTLZGAUS",),  # Annual World Bank/IMF CPI YoY% when quarterly OECD data is unavailable
    "cpi_pl": ("FPCPITOTLZGPOL",),  # Annual World Bank/IMF CPI YoY% fallback when monthly OECD data is unavailable
}

# Series that return raw index values and need FRED units transformation to YoY%.
# CP0000EZ19M086NEST is Eurostat HICP (Index 2015=100) — no OECD YoY% series exists for Euro Area on FRED.
SERIES_YOY_UNITS: dict[str, str] = {
    "CP0000EZ19M086NEST": "pc1",  # Percent Change from Year Ago
    "NZLCPIALLQINMEI": "pc1",  # Percent Change from Year Ago (NZ CPI Index → YoY%)
}

# Manual emergency overrides for stale or historically irregular FRED series.
# Typical quarterly, semiannual, and annual series use FRED metadata-derived lookback instead.
# OECD MEI series: all CPALTT01* series stopped updating on FRED since May 2025
# ("Next Release Date: Not Available"), so stale monthly/quarterly CPI series keep wider overrides.
SERIES_LOOKBACK_DAYS: dict[str, int] = {
    "FPCPITOTLZGJPN": 730,  # Annual JP CPI — need 2-year window
    "FPCPITOTLZGAUS": 730,  # Annual AU CPI fallback — need 2-year window
    "FPCPITOTLZGPOL": 730,  # Annual PL CPI fallback — need 2-year window
    "CPALTT01GBM659N": 540,  # UK CPI (OECD MEI stale since May 2025) — 540 days ensures Mar 2025 obs is in range
    "CPALTT01AUQ659N": 540,  # Quarterly AU CPI (OECD MEI stale since May 2025) — mirrors NZ CPI window
    "CPALTT01CAM659N": 540,  # CA CPI (OECD MEI stale since May 2025) — last obs Mar 2025, 48 days outside 365d window
    "CPALTT01USM659N": 540,  # US CPI (OECD MEI stale since May 2025) — last obs Apr 2025, 17 days outside 365d window
    "CPALTT01CHM659N": 540,  # CH CPI (OECD MEI stale since May 2025) — last obs Apr 2025, 17 days outside 365d window
    "CPALTT01PLM659N": 540,  # PL CPI (OECD MEI stale or delayed) — keep the latest monthly observation in range
}

CACHE_TTL_SECONDS = 86400  # 24h
CACHE_MAX_SIZE = 64
NEGATIVE_CACHE_TTL_SECONDS = 300  # 5m
NEGATIVE_CACHE_MAX_SIZE = 64
METADATA_CACHE_TTL_SECONDS = 86400  # 24h
METADATA_CACHE_MAX_SIZE = 128
METADATA_NEGATIVE_CACHE_TTL_SECONDS = 300  # 5m
METADATA_NEGATIVE_CACHE_MAX_SIZE = 128

_NEGATIVE_CACHE_SENTINEL = object()
_CACHE_MISS = object()

MAX_RETRIES = 3
RETRY_MIN_WAIT_SECONDS = 1
RETRY_MAX_WAIT_SECONDS = 10


def _before_sleep_log(retry_state: RetryCallState) -> None:
    """Log retry attempts without exposing the FRED API key from exception URLs."""
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    safe_msg = sanitize_log_message(str(exc)) if exc else "unknown error"
    logger.warning("FRED: retry attempt %d after error: %s", retry_state.attempt_number, safe_msg)


def _get_indicator_series_chain(indicator_name: str) -> tuple[str, ...]:
    primary_series = FRED_SERIES.get(indicator_name)
    if primary_series is None:
        return ()
    return (primary_series, *FRED_SERIES_FALLBACKS.get(indicator_name, ()))


class FredSource:
    """Fetches macroeconomic data from FRED via fredapi."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or get_settings().FRED_API_KEY
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL_SECONDS)
        self._observation_cache: TTLCache[str, MacroObservation] = TTLCache(
            maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL_SECONDS
        )
        self._negative_cache: TTLCache[str, object] = TTLCache(
            maxsize=NEGATIVE_CACHE_MAX_SIZE,
            ttl=NEGATIVE_CACHE_TTL_SECONDS,
        )
        self._series_info_cache: TTLCache[str, Any] = TTLCache(
            maxsize=METADATA_CACHE_MAX_SIZE,
            ttl=METADATA_CACHE_TTL_SECONDS,
        )
        self._series_info_negative_cache: TTLCache[str, object] = TTLCache(
            maxsize=METADATA_NEGATIVE_CACHE_MAX_SIZE,
            ttl=METADATA_NEGATIVE_CACHE_TTL_SECONDS,
        )
        self._fred: Any | None = None

    def _get_fred(self) -> Any:
        if self._fred is None:
            from fredapi import Fred

            if not self._api_key:
                raise ValueError("FRED_API_KEY is not configured")
            self._fred = Fred(api_key=self._api_key)
        return self._fred

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT_SECONDS, max=RETRY_MAX_WAIT_SECONDS),
        # OSError covers all network-level failures (ConnectionError, TimeoutError, BrokenPipeError, etc.).
        # HTTP-level errors (4xx/5xx from fredapi) are not OSError and are intentionally excluded.
        retry=retry_if_exception_type(OSError),
        before_sleep=_before_sleep_log,
        reraise=True,
    )
    async def _fetch_from_api(self, fred: Any, series_id: str, **kwargs: Any) -> Any:
        """Call FRED API with retry on transient network errors."""
        return await asyncio.to_thread(fred.get_series, series_id, **kwargs)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT_SECONDS, max=RETRY_MAX_WAIT_SECONDS),
        retry=retry_if_exception_type(OSError),
        before_sleep=_before_sleep_log,
        reraise=True,
    )
    async def _fetch_series_info_from_api(self, fred: Any, series_id: str) -> Any:
        """Call FRED metadata API with retry on transient network errors."""
        return await asyncio.to_thread(fred.get_series_info, series_id)

    async def _get_series_frequency_short(self, fred: Any, series_id: str) -> str | None:
        metadata_cache_key = f"fred_meta:{series_id}"
        cached_metadata = self._series_info_cache.get(metadata_cache_key, _CACHE_MISS)
        if cached_metadata is not _CACHE_MISS:
            return self._extract_frequency_short(cached_metadata)

        if metadata_cache_key in self._series_info_negative_cache:
            return None

        try:
            metadata = await self._fetch_series_info_from_api(fred, series_id)
        except Exception as exc:
            safe_msg = sanitize_log_message(str(exc))
            logger.warning("FRED: failed to fetch metadata for series %s: %s", series_id, safe_msg)
            self._series_info_negative_cache[metadata_cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        if metadata is None:
            logger.warning("FRED: no metadata for series %s", series_id)
            self._series_info_negative_cache[metadata_cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        self._series_info_cache[metadata_cache_key] = metadata
        self._series_info_negative_cache.pop(metadata_cache_key, None)
        return self._extract_frequency_short(metadata)

    def _extract_frequency_short(self, metadata: Any) -> str | None:
        frequency_short = None
        get_value = getattr(metadata, "get", None)
        if callable(get_value):
            frequency_short = get_value("frequency_short")
        else:
            try:
                frequency_short = metadata["frequency_short"]
            except (KeyError, TypeError):
                return None

        if not isinstance(frequency_short, str):
            return None

        normalized = frequency_short.strip().upper()
        return normalized or None

    def _lookback_days_for_frequency(self, frequency_short: str | None) -> int | None:
        if frequency_short is None:
            return None
        return FREQUENCY_LOOKBACK_DAYS.get(frequency_short.strip().upper())

    async def _resolve_effective_lookback(self, fred: Any, series_id: str, lookback_days: int) -> int:
        lookback_candidates = [lookback_days]

        manual_override = SERIES_LOOKBACK_DAYS.get(series_id)
        if manual_override is not None:
            lookback_candidates.append(manual_override)

        frequency_short = await self._get_series_frequency_short(fred, series_id)
        frequency_lookback = self._lookback_days_for_frequency(frequency_short)
        if frequency_lookback is not None:
            lookback_candidates.append(frequency_lookback)

        if series_id in SERIES_YOY_UNITS:
            lookback_candidates.append(YOY_UNITS_MIN_LOOKBACK_DAYS)

        return max(lookback_candidates)

    async def fetch_series_observation(
        self, series_id: str, lookback_days: int = DEFAULT_LOOKBACK_DAYS
    ) -> MacroObservation | None:
        """Fetch the latest observation for a FRED series with period metadata."""
        observation_cache_key = f"fred_obs:{series_id}"
        cached_observation = self._observation_cache.get(observation_cache_key)
        if isinstance(cached_observation, MacroObservation):
            return cached_observation

        cache_key = f"fred:{series_id}"
        cached_value = self._cache.get(cache_key)
        if cached_value is not None and cache_key in self._negative_cache:
            # Defensive path: if cache state is inconsistent, negative cache wins.
            return None
        if cache_key in self._negative_cache:
            return None

        try:
            fred = self._get_fred()
            effective_lookback = await self._resolve_effective_lookback(fred, series_id, lookback_days)
            end = datetime.now(UTC)
            start = end - timedelta(days=effective_lookback)
            kwargs: dict[str, Any] = {"observation_start": start, "observation_end": end}
            units = SERIES_YOY_UNITS.get(series_id)
            if units:
                kwargs["units"] = units
            data = await self._fetch_from_api(fred, series_id, **kwargs)
        except Exception as exc:
            safe_msg = sanitize_log_message(str(exc))
            logger.error("FRED: failed to fetch series %s: %s", series_id, safe_msg)
            self._negative_cache[cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        if data is None or data.empty:
            logger.warning("FRED: no data for series %s", series_id)
            self._negative_cache[cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        cleaned = data.dropna()
        if cleaned.empty:
            logger.warning("FRED: no non-null data for series %s", series_id)
            self._negative_cache[cache_key] = _NEGATIVE_CACHE_SENTINEL
            return None

        last_row = cleaned.iloc[-1]
        period_candidate = cleaned.index[-1]
        try:
            period = period_candidate.to_pydatetime().date()
        except Exception:
            # Some test doubles and edge payloads may not carry a datetime index.
            # In that case we keep the value and use current date as observation period.
            period = datetime.now(UTC).date()

        value = float(last_row)
        observation = MacroObservation(value=value, period=period, source="fred", unit="pct_yoy")

        self._cache[cache_key] = value
        self._observation_cache[observation_cache_key] = observation
        self._negative_cache.pop(cache_key, None)
        logger.info("FRED: %s = %.4f", series_id, value)
        return observation

    async def fetch_series(self, series_id: str, lookback_days: int = DEFAULT_LOOKBACK_DAYS) -> float | None:
        """Fetch the latest value for a FRED series.

        Returns the most recent observation value, or None if unavailable.
        """
        cache_key = f"fred:{series_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return float(cached)

        observation = await self.fetch_series_observation(series_id, lookback_days)
        if observation is None:
            return None
        return observation.value

    async def fetch_indicator_observation(
        self, indicator_name: str, lookback_days: int = DEFAULT_LOOKBACK_DAYS
    ) -> MacroObservation | None:
        """Fetch a macro indicator observation with source period metadata."""
        series_chain = _get_indicator_series_chain(indicator_name)
        if not series_chain:
            logger.warning("FRED: unknown indicator name '%s'", indicator_name)
            return None

        for index, series_id in enumerate(series_chain):
            observation = await self.fetch_series_observation(series_id, lookback_days)
            if observation is not None:
                if index > 0:
                    logger.info("FRED: fallback series %s supplied indicator %s", series_id, indicator_name)
                return observation

            has_fallback = index < len(series_chain) - 1
            if has_fallback:
                logger.warning(
                    "FRED: series %s returned no data for indicator %s, trying fallback",
                    series_id,
                    indicator_name,
                )

        return None

    async def fetch_indicator(self, indicator_name: str, lookback_days: int = DEFAULT_LOOKBACK_DAYS) -> float | None:
        """Fetch a macro indicator by its friendly name (e.g. 'fed_funds_rate')."""
        observation = await self.fetch_indicator_observation(indicator_name, lookback_days)
        if observation is None:
            return None
        return observation.value

    async def fetch_multiple(self, indicator_names: list[str]) -> dict[str, float | None]:
        """Fetch multiple indicators at once, returning a dict of results."""
        results: dict[str, float | None] = {}
        for name in indicator_names:
            results[name] = await self.fetch_indicator(name)
        return results

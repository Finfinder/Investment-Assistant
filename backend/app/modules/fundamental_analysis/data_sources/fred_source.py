"""FRED API integration for macroeconomic data."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from cachetools import TTLCache

from app.core.config import get_settings

logger = logging.getLogger(__name__)

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
    "cpi_jp": "FPCPITOTLZGJPN",  # Annual, IMF/World Bank — OECD monthly series discontinued Jun 2021
    "cpi_ch": "CPALTT01CHM659N",
    "cpi_au": "CPALTT01AUQ659N",  # Quarterly, OECD — ABS publishes CPI quarterly, no monthly series on FRED
    "cpi_ca": "CPALTT01CAM659N",
    "boj_rate": "IRSTCI01JPM156N",
    "boe_rate": "IUDSOIA",
    "rba_rate": "IRSTCI01AUM156N",
    "boc_rate": "IRSTCI01CAM156N",
    "snb_rate": "IRSTCI01CHM156N",
    "rbnz_rate": "IRSTCI01NZM156N",
    "cpi_nz": "CPALTT01NZQ659N",  # Quarterly, OECD — Stats NZ publishes CPI quarterly
}

# Series that return raw index values and need FRED units transformation to YoY%.
# CP0000EZ19M086NEST is Eurostat HICP (Index 2015=100) — no OECD YoY% series exists for Euro Area on FRED.
SERIES_YOY_UNITS: dict[str, str] = {
    "CP0000EZ19M086NEST": "pc1",  # Percent Change from Year Ago
}

# Series with lower-than-monthly frequency need wider lookback windows.
# Annual series: 730 days ensures the latest annual observation is always within range.
SERIES_LOOKBACK_DAYS: dict[str, int] = {
    "FPCPITOTLZGJPN": 730,  # Annual JP CPI — need 2-year window
}

CACHE_TTL_SECONDS = 86400  # 24h
CACHE_MAX_SIZE = 64


class FredSource:
    """Fetches macroeconomic data from FRED via fredapi."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or get_settings().FRED_API_KEY
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL_SECONDS)
        self._fred: Any | None = None

    def _get_fred(self) -> Any:
        if self._fred is None:
            from fredapi import Fred

            if not self._api_key:
                raise ValueError("FRED_API_KEY is not configured")
            self._fred = Fred(api_key=self._api_key)
        return self._fred

    async def fetch_series(self, series_id: str, lookback_days: int = 365) -> float | None:
        """Fetch the latest value for a FRED series.

        Returns the most recent observation value, or None if unavailable.
        """
        cache_key = f"fred:{series_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return float(cached)

        try:
            fred = self._get_fred()
            end = datetime.now(UTC)
            effective_lookback = SERIES_LOOKBACK_DAYS.get(series_id, lookback_days)
            start = end - timedelta(days=effective_lookback)
            kwargs: dict[str, Any] = {"observation_start": start, "observation_end": end}
            units = SERIES_YOY_UNITS.get(series_id)
            if units:
                kwargs["units"] = units
            data = await asyncio.to_thread(fred.get_series, series_id, **kwargs)

            if data is None or data.empty:
                logger.warning("FRED: no data for series %s", series_id)
                return None

            value = float(data.dropna().iloc[-1])
            self._cache[cache_key] = value
            logger.info("FRED: %s = %.4f", series_id, value)
            return value

        except Exception:
            logger.warning("FRED: failed to fetch series %s", series_id, exc_info=True)
            return None

    async def fetch_indicator(self, indicator_name: str, lookback_days: int = 365) -> float | None:
        """Fetch a macro indicator by its friendly name (e.g. 'fed_funds_rate')."""
        series_id = FRED_SERIES.get(indicator_name)
        if not series_id:
            logger.warning("FRED: unknown indicator name '%s'", indicator_name)
            return None
        return await self.fetch_series(series_id, lookback_days)

    async def fetch_multiple(self, indicator_names: list[str]) -> dict[str, float | None]:
        """Fetch multiple indicators at once, returning a dict of results."""
        results: dict[str, float | None] = {}
        for name in indicator_names:
            results[name] = await self.fetch_indicator(name)
        return results

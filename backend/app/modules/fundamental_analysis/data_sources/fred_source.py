"""FRED API integration for macroeconomic data."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from cachetools import TTLCache

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# FRED series identifiers for key macro indicators
FRED_SERIES: dict[str, str] = {
    "fed_funds_rate": "FEDFUNDS",
    "cpi_us": "CPIAUCSL",
    "nonfarm_payrolls": "PAYEMS",
    "ism_pmi": "MANEMP",
    "gdp_us": "GDP",
    "unemployment_us": "UNRATE",
    "treasury_10y": "DGS10",
    "treasury_2y": "DGS2",
    "ecb_rate": "ECBDFR",
    "cpi_eu": "CP0000EZ19M086NEST",
    "cpi_uk": "CPALTT01GBM659N",
    "cpi_jp": "CPALTT01JPM659N",
    "cpi_ch": "CPALTT01CHM659N",
    "cpi_au": "CPALTT01AUM659N",
    "cpi_ca": "CPALTT01CAM659N",
    "boj_rate": "IRSTCI01JPM156N",
    "boe_rate": "IUDSOIA",
    "rba_rate": "IRSTCI01AUM156N",
    "boc_rate": "IRSTCI01CAM156N",
    "snb_rate": "IRSTCI01CHM156N",
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

    def fetch_series(self, series_id: str, lookback_days: int = 365) -> float | None:
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
            start = end - timedelta(days=lookback_days)
            data = fred.get_series(series_id, observation_start=start, observation_end=end)

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

    def fetch_indicator(self, indicator_name: str, lookback_days: int = 365) -> float | None:
        """Fetch a macro indicator by its friendly name (e.g. 'fed_funds_rate')."""
        series_id = FRED_SERIES.get(indicator_name)
        if not series_id:
            logger.warning("FRED: unknown indicator name '%s'", indicator_name)
            return None
        return self.fetch_series(series_id, lookback_days)

    def fetch_multiple(self, indicator_names: list[str]) -> dict[str, float | None]:
        """Fetch multiple indicators at once, returning a dict of results."""
        results: dict[str, float | None] = {}
        for name in indicator_names:
            results[name] = self.fetch_indicator(name)
        return results

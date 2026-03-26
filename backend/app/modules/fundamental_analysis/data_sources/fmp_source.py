"""FMP API integration for economic data and COT reports."""

import logging
from typing import Any

import httpx
from cachetools import TTLCache

from app.core.config import get_settings
from app.core.daily_rate_limiter import DailyRateLimiter

logger = logging.getLogger(__name__)

FMP_BASE_URL = "https://financialmodelingprep.com/api"
DAILY_RATE_LIMIT = 250
CACHE_TTL_SECONDS = 86400  # 24h
CACHE_MAX_SIZE = 128


class FmpEconomicSource:
    """Fetches economic data and COT reports from Financial Modeling Prep API."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or get_settings().FMP_API_KEY
        self._rate_limiter = DailyRateLimiter(DAILY_RATE_LIMIT, "FMP")
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL_SECONDS)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Perform a GET request to FMP API with rate limiting and caching."""
        self._rate_limiter.check()

        cache_key = f"fmp:{path}:{params}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        request_params: dict[str, Any] = {"apikey": self._api_key}
        if params:
            request_params.update(params)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{FMP_BASE_URL}{path}", params=request_params)
            self._rate_limiter.increment()

            if resp.status_code == 429:
                raise RuntimeError("FMP rate limit (429 Too Many Requests)")
            resp.raise_for_status()
            data = resp.json()

        self._cache[cache_key] = data
        return data

    # ---- Economic Data (Task 5.2) ----

    async def fetch_treasury_rates(self) -> dict[str, float | None]:
        """Fetch latest US Treasury rates from FMP."""
        try:
            data = await self._get("/v4/treasury")
            if not data:
                return {}
            latest = data[0] if isinstance(data, list) else data
            return {
                "treasury_1m": latest.get("month1"),
                "treasury_3m": latest.get("month3"),
                "treasury_6m": latest.get("month6"),
                "treasury_1y": latest.get("year1"),
                "treasury_2y": latest.get("year2"),
                "treasury_5y": latest.get("year5"),
                "treasury_10y": latest.get("year10"),
                "treasury_30y": latest.get("year30"),
            }
        except Exception:
            logger.warning("FMP: failed to fetch treasury rates", exc_info=True)
            return {}

    async def fetch_economic_indicator(self, name: str) -> float | None:
        """Fetch a specific economic indicator from FMP by name.

        Supported names: GDP, realGDP, CPI, inflationRate, interestRate,
        unemployment, retailSales, etc.
        """
        try:
            data = await self._get("/v4/economic", params={"name": name})
            if not data or not isinstance(data, list):
                return None
            return float(data[0].get("value", 0))
        except Exception:
            logger.warning("FMP: failed to fetch economic indicator '%s'", name, exc_info=True)
            return None

    async def fetch_economic_calendar(self, country: str = "US", limit: int = 50) -> list[dict[str, Any]]:
        """Fetch upcoming economic events from FMP."""
        try:
            data = await self._get("/v3/economic_calendar", params={"limit": limit})
            if not data or not isinstance(data, list):
                return []
            return [e for e in data if e.get("country", "").upper() == country.upper()]
        except Exception:
            logger.warning("FMP: failed to fetch economic calendar", exc_info=True)
            return []

    # ---- COT Reports (Task 5.3) ----

    async def fetch_cot_report(self, symbol: str) -> dict[str, Any] | None:
        """Fetch latest COT (Commitment of Traders) report for a commodity symbol.

        Returns parsed positions: commercial, non-commercial, non-reportable,
        net positions, and week-over-week changes.
        """
        try:
            data = await self._get(f"/v4/commitment_of_traders_report/{symbol.upper()}")
            if not data or not isinstance(data, list) or len(data) < 1:
                logger.warning("FMP: no COT data for %s", symbol)
                return None

            latest = data[0]
            previous = data[1] if len(data) > 1 else None

            commercial_long = latest.get("commercialLong", 0) or 0
            commercial_short = latest.get("commercialShort", 0) or 0
            non_commercial_long = latest.get("nonCommercialLong", 0) or 0
            non_commercial_short = latest.get("nonCommercialShort", 0) or 0
            non_reportable_long = latest.get("nonReportableLong", 0) or 0
            non_reportable_short = latest.get("nonReportableShort", 0) or 0

            net_commercial = commercial_long - commercial_short
            net_non_commercial = non_commercial_long - non_commercial_short
            net_non_reportable = non_reportable_long - non_reportable_short

            result: dict[str, Any] = {
                "date": latest.get("date"),
                "commercial_long": commercial_long,
                "commercial_short": commercial_short,
                "net_commercial": net_commercial,
                "non_commercial_long": non_commercial_long,
                "non_commercial_short": non_commercial_short,
                "net_non_commercial": net_non_commercial,
                "non_reportable_long": non_reportable_long,
                "non_reportable_short": non_reportable_short,
                "net_non_reportable": net_non_reportable,
            }

            if previous:
                prev_net_nc = (previous.get("nonCommercialLong", 0) or 0) - (previous.get("nonCommercialShort", 0) or 0)
                result["net_non_commercial_change"] = net_non_commercial - prev_net_nc
                prev_net_c = (previous.get("commercialLong", 0) or 0) - (previous.get("commercialShort", 0) or 0)
                result["net_commercial_change"] = net_commercial - prev_net_c

            return result

        except Exception:
            logger.warning("FMP: failed to fetch COT report for %s", symbol, exc_info=True)
            return None

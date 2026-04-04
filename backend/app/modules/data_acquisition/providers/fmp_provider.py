import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.daily_rate_limiter import DailyRateLimiter
from app.core.models import OHLCVData, Timeframe
from app.modules.data_acquisition.interfaces import DataProviderPriority

logger = logging.getLogger(__name__)

BASE_URL = "https://financialmodelingprep.com/api/v3"

TIMEFRAME_MAP: dict[Timeframe, str] = {
    Timeframe.M15: "15min",
    Timeframe.H1: "1hour",
    Timeframe.H4: "4hour",
    Timeframe.D1: "1day",
}

DAILY_RATE_LIMIT = 250

SYMBOL_MAP: dict[str, str] = {
    # Forex majors
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "USDCHF": "USDCHF",
    "AUDUSD": "AUDUSD",
    "USDCAD": "USDCAD",
    "NZDUSD": "NZDUSD",
    "EURGBP": "EURGBP",
    "EURJPY": "EURJPY",
    "GBPJPY": "GBPJPY",
    # Forex cross pairs
    "AUDCAD": "AUDCAD",
    "AUDCHF": "AUDCHF",
    "AUDJPY": "AUDJPY",
    "CADJPY": "CADJPY",
    "CHFJPY": "CHFJPY",
    "EURCHF": "EURCHF",
    "EURAUD": "EURAUD",
    "EURCAD": "EURCAD",
    "GBPCAD": "GBPCAD",
    "GBPCHF": "GBPCHF",
    "AUDNZD": "AUDNZD",
    "NZDJPY": "NZDJPY",
    "NZDCAD": "NZDCAD",
    "NZDCHF": "NZDCHF",
    "EURNZD": "EURNZD",
    "GBPNZD": "GBPNZD",
    # Commodities
    "GOLD": "XAUUSD",
    "XAUUSD": "XAUUSD",
    "SILVER": "XAGUSD",
    "XAGUSD": "XAGUSD",
    "OIL": "CLUSD",
    "WTIUSD": "CLUSD",
    "US500": "^GSPC",
    "US30": "^DJI",
    "US100": "^IXIC",
}


class FMPProvider:
    """TERTIARY data provider using Financial Modeling Prep REST API."""

    def __init__(self, api_key: str) -> None:
        self._name = "fmp"
        self._priority = DataProviderPriority.TERTIARY
        self._api_key = api_key
        self._rate_limiter = DailyRateLimiter(DAILY_RATE_LIMIT, "FMP")

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> DataProviderPriority:
        return self._priority

    def get_supported_symbols(self) -> list[str]:
        return list(SYMBOL_MAP.keys())

    def _map_symbol(self, symbol: str) -> str:
        key = symbol.upper().replace("/", "")
        return SYMBOL_MAP.get(key, key)

    async def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            self._rate_limiter.check()
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{BASE_URL}/stock/list",
                    params={"apikey": self._api_key},
                )
                return resp.status_code == 200
        except Exception:
            logger.warning("FMP availability check failed", exc_info=True)
            return False

    async def fetch_ohlcv(self, symbol: str, timeframe: Timeframe, period: str) -> list[OHLCVData]:
        self._rate_limiter.check()

        fmp_symbol = self._map_symbol(symbol)
        fmp_interval = TIMEFRAME_MAP[timeframe]

        if timeframe == Timeframe.D1:
            url = f"{BASE_URL}/historical-price-full/{fmp_symbol}"
        else:
            url = f"{BASE_URL}/historical-chart/{fmp_interval}/{fmp_symbol}"

        logger.info("FMP: fetching %s interval=%s", fmp_symbol, fmp_interval)

        params: dict[str, str | int] = {"apikey": self._api_key}
        if timeframe == Timeframe.D1:
            params["timeseries"] = self._period_to_days(period)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            self._rate_limiter.increment()

            if resp.status_code == 429:
                raise RuntimeError("FMP rate limit (429 Too Many Requests)")

            resp.raise_for_status()
            data = resp.json()

        return self._parse_response(data, timeframe)

    def _parse_response(self, data: Any, timeframe: Timeframe) -> list[OHLCVData]:
        if timeframe == Timeframe.D1:
            items = data.get("historical", []) if isinstance(data, dict) else []
        else:
            items = data if isinstance(data, list) else []

        if not items:
            logger.warning("FMP returned no data")
            return []

        result: list[OHLCVData] = []
        for item in items:
            dt_str = item.get("date", "")
            try:
                ts = datetime.fromisoformat(dt_str).replace(tzinfo=UTC)
            except ValueError:
                continue

            result.append(
                OHLCVData(
                    timestamp=ts,
                    open=float(item["open"]),
                    high=float(item["high"]),
                    low=float(item["low"]),
                    close=float(item["close"]),
                    volume=float(item.get("volume", 0)),
                )
            )

        # FMP returns newest first, reverse to chronological order
        result.reverse()

        logger.info("FMP: returned %d candles", len(result))
        return result

    @staticmethod
    def _period_to_days(period: str) -> int:
        num = int(period[:-1])
        unit = period[-1].lower()
        if unit == "y":
            return num * 365
        return num

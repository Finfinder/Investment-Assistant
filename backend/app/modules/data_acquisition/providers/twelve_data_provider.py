import logging
from datetime import UTC, datetime

import httpx

from app.core.daily_rate_limiter import DailyRateLimiter
from app.core.models import OHLCVData, Timeframe
from app.modules.data_acquisition.interfaces import DataProviderPriority

logger = logging.getLogger(__name__)

BASE_URL = "https://api.twelvedata.com"

TIMEFRAME_MAP: dict[Timeframe, str] = {
    Timeframe.M15: "15min",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",
    Timeframe.D1: "1day",
}

DAILY_RATE_LIMIT = 800


class TwelveDataProvider:
    """SECONDARY data provider using Twelve Data REST API."""

    def __init__(self, api_key: str) -> None:
        self._name = "twelve_data"
        self._priority = DataProviderPriority.SECONDARY
        self._api_key = api_key
        self._rate_limiter = DailyRateLimiter(DAILY_RATE_LIMIT, "Twelve Data")

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> DataProviderPriority:
        return self._priority

    def get_supported_symbols(self) -> list[str]:
        return ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "SILVER", "OIL", "US500", "US30", "US100"]

    def _map_symbol(self, symbol: str) -> str:
        key = symbol.upper().replace("/", "")
        forex_pairs = {
            "EURUSD",
            "GBPUSD",
            "USDJPY",
            "USDCHF",
            "AUDUSD",
            "USDCAD",
            "NZDUSD",
            "EURGBP",
            "EURJPY",
            "GBPJPY",
        }
        if key in forex_pairs:
            return f"{key[:3]}/{key[3:]}"

        commodity_map = {
            "GOLD": "XAU/USD",
            "XAUUSD": "XAU/USD",
            "SILVER": "XAG/USD",
            "XAGUSD": "XAG/USD",
            "OIL": "CL",
            "WTIUSD": "CL",
            "BRENT": "BZ",
            "NATGAS": "NG",
        }
        if key in commodity_map:
            return commodity_map[key]

        index_map = {
            "US500": "SPX",
            "US30": "DJI",
            "US100": "IXIC",
            "DE40": "DAX",
            "UK100": "FTSE",
            "JP225": "NI225",
        }
        if key in index_map:
            return index_map[key]

        return key

    async def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            self._rate_limiter.check()
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{BASE_URL}/api_usage", params={"apikey": self._api_key})
                return resp.status_code == 200
        except Exception:
            logger.warning("Twelve Data availability check failed", exc_info=True)
            return False

    async def fetch_ohlcv(self, symbol: str, timeframe: Timeframe, period: str) -> list[OHLCVData]:
        self._rate_limiter.check()

        td_symbol = self._map_symbol(symbol)
        td_interval = TIMEFRAME_MAP[timeframe]
        outputsize = self._period_to_outputsize(period, timeframe)

        logger.info("TwelveData: fetching %s interval=%s outputsize=%d", td_symbol, td_interval, outputsize)

        params: dict[str, str | int] = {
            "symbol": td_symbol,
            "interval": td_interval,
            "outputsize": outputsize,
            "apikey": self._api_key,
            "format": "JSON",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{BASE_URL}/time_series", params=params)
            self._rate_limiter.increment()

            if resp.status_code == 429:
                raise RuntimeError("Twelve Data rate limit (429 Too Many Requests)")

            resp.raise_for_status()
            data = resp.json()

        if "code" in data and data["code"] != 200:
            msg = data.get("message", "Unknown error")
            logger.error("TwelveData API error: %s", msg)
            raise RuntimeError(f"Twelve Data error: {msg}")

        values = data.get("values", [])
        if not values:
            logger.warning("TwelveData returned no data for %s", td_symbol)
            return []

        result: list[OHLCVData] = []
        for item in values:
            result.append(
                OHLCVData(
                    timestamp=datetime.fromisoformat(item["datetime"]).replace(tzinfo=UTC),
                    open=float(item["open"]),
                    high=float(item["high"]),
                    low=float(item["low"]),
                    close=float(item["close"]),
                    volume=float(item.get("volume", 0)),
                )
            )

        # API returns newest first, reverse to chronological order
        result.reverse()

        logger.info("TwelveData: returned %d candles for %s", len(result), td_symbol)
        return result

    @staticmethod
    def _period_to_outputsize(period: str, timeframe: Timeframe) -> int:
        num = int(period[:-1])
        unit = period[-1].lower()
        days = num if unit == "d" else num * 365

        candles_per_day = {
            Timeframe.M15: 96,
            Timeframe.H1: 24,
            Timeframe.H4: 6,
            Timeframe.D1: 1,
        }
        return min(days * candles_per_day[timeframe], 5000)

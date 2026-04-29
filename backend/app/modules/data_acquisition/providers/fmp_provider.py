import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.daily_rate_limiter import DailyRateLimiter
from app.core.models import OHLCVData
from app.modules.data_acquisition.interfaces import DataProviderPriority
from app.modules.data_acquisition.timeframes import DataTimeframe, TimeframeLike, normalize_data_timeframe

logger = logging.getLogger(__name__)

BASE_URL = "https://financialmodelingprep.com/api/v3"

TIMEFRAME_MAP: dict[DataTimeframe, str] = {
    DataTimeframe.M15: "15min",
    DataTimeframe.H1: "1hour",
    DataTimeframe.H4: "4hour",
    DataTimeframe.D1: "1day",
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
    # PLN pairs
    "AUDPLN": "AUDPLN",
    "CADPLN": "CADPLN",
    "CHFPLN": "CHFPLN",
    "EURPLN": "EURPLN",
    "GBPPLN": "GBPPLN",
    "JPYPLN": "JPYPLN",
    "USDPLN": "USDPLN",
    # Commodities
    "GOLD": "XAUUSD",
    "XAUUSD": "XAUUSD",
    "SILVER": "XAGUSD",
    "XAGUSD": "XAGUSD",
    "OIL": "CLUSD",
    "WTIUSD": "CLUSD",
    "OILWTI": "CLUSD",
    "BRENT": "BZUSD",
    "NATGAS": "NGUSD",
    "COFFEE": "KCUSD",
    "COPPER": "HGUSD",
    "PLATINUM": "PLUSD",
    "PALLADIUM": "PAUSD",
    # Indices
    "US500": "^GSPC",
    "US30": "^DJI",
    "US100": "^IXIC",
    "W20": "WIG20",
}


def _build_weekly_candle(candles: list[OHLCVData]) -> OHLCVData:
    return OHLCVData(
        timestamp=candles[0].timestamp,
        open=candles[0].open,
        high=max(candle.high for candle in candles),
        low=min(candle.low for candle in candles),
        close=candles[-1].close,
        volume=sum(candle.volume for candle in candles),
    )


def _resample_to_weekly(candles: list[OHLCVData]) -> list[OHLCVData]:
    if not candles:
        return []

    result: list[OHLCVData] = []
    bucket: list[OHLCVData] = []
    current_week: tuple[int, int] | None = None

    for candle in candles:
        iso_week = candle.timestamp.isocalendar()
        week_key = (iso_week.year, iso_week.week)

        if current_week is None or week_key == current_week:
            current_week = week_key
            bucket.append(candle)
            continue

        result.append(_build_weekly_candle(bucket))
        current_week = week_key
        bucket = [candle]

    if bucket:
        result.append(_build_weekly_candle(bucket))

    return result


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

    async def fetch_ohlcv(self, symbol: str, timeframe: TimeframeLike, period: str) -> list[OHLCVData]:
        data_timeframe = normalize_data_timeframe(timeframe)

        if data_timeframe == DataTimeframe.W1:
            logger.info("FMP: resampling weekly candles from daily data for %s", symbol)
            daily = await self.fetch_ohlcv(symbol, DataTimeframe.D1, period)
            return _resample_to_weekly(daily)

        self._rate_limiter.check()

        fmp_symbol = self._map_symbol(symbol)
        fmp_interval = TIMEFRAME_MAP[data_timeframe]

        if data_timeframe == DataTimeframe.D1:
            url = f"{BASE_URL}/historical-price-full/{fmp_symbol}"
        else:
            url = f"{BASE_URL}/historical-chart/{fmp_interval}/{fmp_symbol}"

        logger.info("FMP: fetching %s interval=%s", fmp_symbol, fmp_interval)

        params: dict[str, str | int] = {"apikey": self._api_key}
        if data_timeframe == DataTimeframe.D1:
            params["timeseries"] = self._period_to_days(period)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            self._rate_limiter.increment()

            if resp.status_code == 429:
                raise RuntimeError("FMP rate limit (429 Too Many Requests)")

            resp.raise_for_status()
            data = resp.json()

        return self._parse_response(data, data_timeframe)

    def _parse_response(self, data: Any, timeframe: DataTimeframe) -> list[OHLCVData]:
        if timeframe == DataTimeframe.D1:
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

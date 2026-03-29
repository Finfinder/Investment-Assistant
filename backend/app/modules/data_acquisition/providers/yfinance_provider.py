import asyncio
import logging
from datetime import UTC

import yfinance as yf

from app.core.models import OHLCVData, Timeframe
from app.modules.data_acquisition.interfaces import DataProviderPriority

logger = logging.getLogger(__name__)

SYMBOL_MAP: dict[str, str] = {
    # Forex
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "USDCHF": "USDCHF=X",
    "AUDUSD": "AUDUSD=X",
    "USDCAD": "USDCAD=X",
    "NZDUSD": "NZDUSD=X",
    "EURGBP": "EURGBP=X",
    "EURJPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X",
    # Forex cross pairs
    "AUDCAD": "AUDCAD=X",
    "AUDCHF": "AUDCHF=X",
    "AUDJPY": "AUDJPY=X",
    "CADJPY": "CADJPY=X",
    "CHFJPY": "CHFJPY=X",
    "EURCHF": "EURCHF=X",
    "EURAUD": "EURAUD=X",
    "EURCAD": "EURCAD=X",
    "GBPCAD": "GBPCAD=X",
    "GBPCHF": "GBPCHF=X",
    # Commodities
    "GOLD": "GC=F",
    "XAUUSD": "GC=F",
    "SILVER": "SI=F",
    "XAGUSD": "SI=F",
    "OIL": "CL=F",
    "WTIUSD": "CL=F",
    "BRENT": "BZ=F",
    "NATGAS": "NG=F",
    # Indices
    "US500": "^GSPC",
    "US30": "^DJI",
    "US100": "^IXIC",
    "DE40": "^GDAXI",
    "UK100": "^FTSE",
    "JP225": "^N225",
    "FR40": "^FCHI",
}

TIMEFRAME_MAP: dict[Timeframe, str] = {
    Timeframe.M15: "15m",
    Timeframe.H1: "1h",
    Timeframe.H4: "1h",  # yfinance doesn't support 4h natively; we resample
    Timeframe.D1: "1d",
}

# yfinance restricts intraday intervals to short periods
PERIOD_LIMITS: dict[str, str] = {
    "15m": "60d",
    "1h": "730d",
    "1d": "10y",
}


def _map_symbol(symbol: str) -> str:
    key = symbol.upper().replace("/", "")
    mapped = SYMBOL_MAP.get(key)
    if mapped:
        return mapped
    # If not in map, try using the symbol directly (e.g. AAPL)
    return key


def _clamp_period(period: str, yf_interval: str) -> str:
    """Clamp requested period to yfinance's maximum for the interval."""
    max_period = PERIOD_LIMITS.get(yf_interval)
    if not max_period:
        return period

    def _period_to_days(p: str) -> int:
        num = int(p[:-1])
        unit = p[-1].lower()
        if unit == "d":
            return num
        if unit == "y":
            return num * 365
        return num  # fallback

    requested = _period_to_days(period)
    maximum = _period_to_days(max_period)
    if requested > maximum:
        logger.warning("Period %s exceeds yfinance limit %s for interval %s, clamping", period, max_period, yf_interval)
        return max_period
    return period


def _resample_to_4h(data: list[OHLCVData]) -> list[OHLCVData]:
    """Resample 1h OHLCV data into 4h candles."""
    if not data:
        return []

    result: list[OHLCVData] = []
    bucket: list[OHLCVData] = []

    for candle in data:
        bucket.append(candle)
        if len(bucket) == 4:
            result.append(
                OHLCVData(
                    timestamp=bucket[0].timestamp,
                    open=bucket[0].open,
                    high=max(c.high for c in bucket),
                    low=min(c.low for c in bucket),
                    close=bucket[-1].close,
                    volume=sum(c.volume for c in bucket),
                )
            )
            bucket = []

    # Discard incomplete bucket to keep clean 4h candles
    return result


class YFinanceProvider:
    """PRIMARY data provider using the yfinance library."""

    def __init__(self) -> None:
        self._name = "yfinance"
        self._priority = DataProviderPriority.PRIMARY

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> DataProviderPriority:
        return self._priority

    def get_supported_symbols(self) -> list[str]:
        return list(SYMBOL_MAP.keys())

    async def is_available(self) -> bool:
        try:
            ticker = yf.Ticker("AAPL")
            info = await asyncio.to_thread(lambda: ticker.fast_info)
            return info is not None
        except Exception:
            logger.warning("yfinance availability check failed", exc_info=True)
            return False

    async def fetch_ohlcv(self, symbol: str, timeframe: Timeframe, period: str) -> list[OHLCVData]:
        yf_symbol = _map_symbol(symbol)
        yf_interval = TIMEFRAME_MAP[timeframe]
        yf_period = _clamp_period(period, yf_interval)

        logger.info("yfinance: fetching %s interval=%s period=%s", yf_symbol, yf_interval, yf_period)

        ticker = yf.Ticker(yf_symbol)
        df = await asyncio.to_thread(ticker.history, period=yf_period, interval=yf_interval)

        if df is None or df.empty:
            logger.warning("yfinance returned no data for %s", yf_symbol)
            return []

        result: list[OHLCVData] = []
        for ts, row in df.iterrows():
            ts_dt = ts.to_pydatetime()
            if ts_dt.tzinfo is None:
                ts_dt = ts_dt.replace(tzinfo=UTC)
            result.append(
                OHLCVData(
                    timestamp=ts_dt,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row.get("Volume", 0)),
                )
            )

        if timeframe == Timeframe.H4:
            result = _resample_to_4h(result)

        logger.info("yfinance: returned %d candles for %s", len(result), yf_symbol)
        return result

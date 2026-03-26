import logging
import re
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.models import OHLCVData, Timeframe
from app.modules.data_acquisition.cache import InMemoryCache, make_cache_key
from app.modules.data_acquisition.fallback_chain import DataProviderError, FallbackChainManager
from app.modules.data_acquisition.providers.fmp_provider import FMPProvider
from app.modules.data_acquisition.providers.twelve_data_provider import TwelveDataProvider
from app.modules.data_acquisition.providers.yfinance_provider import YFinanceProvider

if TYPE_CHECKING:
    from app.modules.data_acquisition.interfaces import DataProvider

logger = logging.getLogger(__name__)

router = APIRouter(tags=["market-data"])

SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9]{2,20}$")
PERIOD_PATTERN = re.compile(r"^\d{1,4}[dymDYM]$")

# Module-level singletons (created once on first import)
_intraday_cache: InMemoryCache | None = None
_daily_cache: InMemoryCache | None = None
_chain: FallbackChainManager | None = None


def _get_caches() -> tuple[InMemoryCache, InMemoryCache]:
    global _intraday_cache, _daily_cache
    if _intraday_cache is None:
        settings = get_settings()
        _intraday_cache = InMemoryCache(default_ttl=settings.CACHE_TTL_INTRADAY)
        _daily_cache = InMemoryCache(default_ttl=settings.CACHE_TTL_DAILY)
    assert _daily_cache is not None
    return _intraday_cache, _daily_cache


def _get_chain() -> FallbackChainManager:
    global _chain
    if _chain is None:
        settings = get_settings()
        providers: list[DataProvider] = [YFinanceProvider()]
        if settings.TWELVE_DATA_API_KEY:
            providers.append(TwelveDataProvider(api_key=settings.TWELVE_DATA_API_KEY))
        if settings.FMP_API_KEY:
            providers.append(FMPProvider(api_key=settings.FMP_API_KEY))
        _chain = FallbackChainManager(providers)
    return _chain


def get_fallback_chain() -> FallbackChainManager:
    """Public accessor for the fallback chain (allows DI override in tests)."""
    return _get_chain()


@router.get("/market-data/{symbol}", response_model=list[OHLCVData])
async def get_market_data(
    symbol: str,
    timeframe: Timeframe = Timeframe.H1,
    period: str = "30d",
) -> list[OHLCVData]:
    # Validate symbol
    if not SYMBOL_PATTERN.match(symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol format")

    # Validate period
    if not PERIOD_PATTERN.match(period):
        raise HTTPException(status_code=400, detail="Invalid period format (e.g. 30d, 6m, 1y)")

    # Select cache based on timeframe
    intraday_cache, daily_cache = _get_caches()
    cache = daily_cache if timeframe == Timeframe.D1 else intraday_cache

    cache_key = make_cache_key(symbol, timeframe.value, period)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[no-any-return]

    chain = get_fallback_chain()

    try:
        data = await chain.fetch_ohlcv(symbol, timeframe, period)
    except DataProviderError as exc:
        logger.error("All providers failed: %s", exc)
        raise HTTPException(status_code=502, detail="Unable to fetch market data from any provider") from exc

    if data:
        cache.set(cache_key, data)

    return data

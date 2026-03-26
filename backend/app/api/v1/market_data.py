import logging
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Request

from app.api.v1.validators import validate_period, validate_symbol
from app.core.config import get_settings
from app.core.models import OHLCVData, Timeframe
from app.core.rate_limit import limiter
from app.modules.data_acquisition.cache import InMemoryCache, make_cache_key
from app.modules.data_acquisition.fallback_chain import (
    DataProviderError,
    FallbackChainManager,
    build_fallback_chain,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["market-data"])


@lru_cache(maxsize=1)
def _get_caches() -> tuple[InMemoryCache, InMemoryCache]:
    settings = get_settings()
    intraday_cache = InMemoryCache(default_ttl=settings.CACHE_TTL_INTRADAY)
    daily_cache = InMemoryCache(default_ttl=settings.CACHE_TTL_DAILY)
    return intraday_cache, daily_cache


@lru_cache(maxsize=1)
def _get_chain() -> FallbackChainManager:
    return build_fallback_chain()


def get_fallback_chain() -> FallbackChainManager:
    """Public accessor for the fallback chain (allows DI override in tests)."""
    return _get_chain()


@router.get("/market-data/{symbol}", response_model=list[OHLCVData])
@limiter.limit("30/minute")
async def get_market_data(
    request: Request,
    symbol: str,
    timeframe: Timeframe = Timeframe.H1,
    period: str = "30d",
) -> list[OHLCVData]:
    validate_symbol(symbol)
    validate_period(period)

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

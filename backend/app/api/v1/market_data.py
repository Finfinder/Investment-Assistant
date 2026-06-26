import logging
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Request

from app.api.v1.validators import validate_period, validate_symbol
from app.core.config import get_settings
from app.core.models import OHLCVData, Timeframe
from app.core.rate_limit import limiter
from app.modules.data_acquisition.cache import make_cache_key
from app.modules.data_acquisition.fallback_chain import (
    DataProviderError,
    FallbackChainManager,
    build_fallback_chain,
)
from app.modules.data_acquisition.redis_cache import RedisCache, create_redis_cache

logger = logging.getLogger(__name__)

router = APIRouter(tags=["market-data"])


@lru_cache(maxsize=1)
def _get_caches() -> tuple["RedisCache", "RedisCache"]:
    settings = get_settings()
    ttl_override = settings.REDIS_CACHE_TTL_OVERRIDE
    intraday_cache = create_redis_cache(default_ttl=ttl_override or settings.CACHE_TTL_INTRADAY, key_prefix="ohlcv")
    daily_cache = create_redis_cache(default_ttl=ttl_override or settings.CACHE_TTL_DAILY, key_prefix="ohlcv")
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
    cached = await cache.get(cache_key)
    if cached is not None:
        return [OHLCVData(**item) for item in cached]

    chain = get_fallback_chain()

    try:
        data = await chain.fetch_ohlcv(symbol, timeframe, period)
    except DataProviderError as exc:
        logger.error("All providers failed: %s", exc)
        raise HTTPException(status_code=502, detail="Unable to fetch market data from any provider") from exc

    if data:
        serialized_data = [item.model_dump(mode="json") for item in data]
        await cache.set(cache_key, serialized_data)

    return data

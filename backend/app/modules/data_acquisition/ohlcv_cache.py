"""OHLCV cache service — delta-fetch strategy with SQLite persistence."""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import OHLCVCache
from app.core.models import OHLCVData

# Type alias for the async fetch function passed to OHLCVCacheService
FetchFn = Callable[[str, str, str], Awaitable[list[OHLCVData]]]

logger = logging.getLogger(__name__)

# Staleness threshold: if fetched_at is older than this, re-fetch recent candles
_STALENESS_MINUTES = 5

# Timeframes considered intraday (subject to staleness check)
_INTRADAY_TIMEFRAMES = frozenset({"M15", "H1", "H4"})

# Max rows per INSERT statement (500 x 8 columns = 4000 params, safely under SQLite 32766 limit)
_UPSERT_CHUNK_SIZE = 500


async def get_cached_ohlcv(session: AsyncSession, symbol: str, timeframe: str) -> list[OHLCVData]:
    """Return all cached candles for symbol+timeframe, ordered by timestamp."""
    result = await session.execute(
        select(OHLCVCache)
        .where(OHLCVCache.symbol == symbol, OHLCVCache.timeframe == timeframe)
        .order_by(OHLCVCache.timestamp)
    )
    rows = result.scalars().all()
    return [
        OHLCVData(
            timestamp=row.timestamp,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
        )
        for row in rows
    ]


async def get_latest_timestamp(session: AsyncSession, symbol: str, timeframe: str) -> datetime | None:
    """Return the most recent cached candle timestamp, or None if empty."""
    result = await session.execute(
        select(OHLCVCache.timestamp)
        .where(OHLCVCache.symbol == symbol, OHLCVCache.timeframe == timeframe)
        .order_by(OHLCVCache.timestamp.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_fetched_at(session: AsyncSession, symbol: str, timeframe: str) -> datetime | None:
    """Return the most recent fetched_at timestamp for the newest cached candle."""
    result = await session.execute(
        select(func.max(OHLCVCache.fetched_at)).where(OHLCVCache.symbol == symbol, OHLCVCache.timeframe == timeframe)
    )
    return result.scalar_one_or_none()


async def upsert_ohlcv(session: AsyncSession, symbol: str, timeframe: str, candles: list[OHLCVData]) -> int:
    """Insert or update candles in cache using bulk upsert. Returns count of rows written."""
    if not candles:
        return 0

    rows = [
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        }
        for c in candles
    ]

    for i in range(0, len(rows), _UPSERT_CHUNK_SIZE):
        chunk = rows[i : i + _UPSERT_CHUNK_SIZE]
        stmt = sqlite_insert(OHLCVCache).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "timeframe", "timestamp"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "fetched_at": func.now(),
            },
        )
        await session.execute(stmt)

    await session.commit()
    logger.info("Cached %d candles for %s/%s", len(candles), symbol, timeframe)
    return len(candles)


async def clear_cache(session: AsyncSession, symbol: str, timeframe: str) -> None:
    """Remove all cached candles for a symbol+timeframe pair."""
    await session.execute(delete(OHLCVCache).where(OHLCVCache.symbol == symbol, OHLCVCache.timeframe == timeframe))
    await session.commit()


def _is_stale(fetched_at: datetime | None, timeframe: str) -> bool:
    """Check if cached data is stale for intraday timeframes."""
    if timeframe not in _INTRADAY_TIMEFRAMES:
        return False
    if fetched_at is None:
        return True
    now = datetime.now(UTC).replace(tzinfo=None)
    return (now - fetched_at) > timedelta(minutes=_STALENESS_MINUTES)


class OHLCVCacheService:
    """Delta-fetch cache: query DB -> fetch only missing candles -> upsert -> return full set."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        period: str,
        fetch_fn: FetchFn,
    ) -> list[OHLCVData]:
        """Main entry point. Returns candles from cache, fetching missing data via fetch_fn."""
        latest_ts = await get_latest_timestamp(self._session, symbol, timeframe)
        fetched_at = await get_latest_fetched_at(self._session, symbol, timeframe)

        if latest_ts is None:
            # Cache miss — full fetch
            logger.info("Cache MISS for %s/%s — full fetch", symbol, timeframe)
            candles = await fetch_fn(symbol, timeframe, period)
            if candles:
                await upsert_ohlcv(self._session, symbol, timeframe, candles)
            return candles

        if _is_stale(fetched_at, timeframe):
            # Stale data — re-fetch full dataset for freshness
            logger.info("Cache STALE for %s/%s (fetched_at=%s) — full re-fetch", symbol, timeframe, fetched_at)
            candles = await fetch_fn(symbol, timeframe, period)
            if candles:
                await upsert_ohlcv(self._session, symbol, timeframe, candles)
                return candles
            # If re-fetch fails, fall back to cached data
            logger.warning("Re-fetch returned empty for %s/%s, using cached data", symbol, timeframe)
            return await get_cached_ohlcv(self._session, symbol, timeframe)

        # Cache hit — try delta fetch (only new candles since latest_ts)
        logger.info("Cache HIT for %s/%s (latest=%s) — delta fetch", symbol, timeframe, latest_ts)
        try:
            fresh_candles = await fetch_fn(symbol, timeframe, period)
            if fresh_candles:
                # Filter to only candles newer than or at latest_ts (to update unclosed candle)
                # Use naive comparison since SQLite strips tzinfo
                latest_naive = latest_ts if latest_ts.tzinfo is None else latest_ts.replace(tzinfo=None)
                delta = [c for c in fresh_candles if c.timestamp.replace(tzinfo=None) >= latest_naive]
                if delta:
                    await upsert_ohlcv(self._session, symbol, timeframe, delta)
                    logger.info("Delta-fetched %d candles for %s/%s", len(delta), symbol, timeframe)
        except Exception as exc:
            logger.warning("Delta fetch failed for %s/%s: %s — returning cached data", symbol, timeframe, exc)

        return await get_cached_ohlcv(self._session, symbol, timeframe)

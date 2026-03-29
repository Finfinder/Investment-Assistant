from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.core.models import OHLCVData
from app.modules.data_acquisition.ohlcv_cache import (
    OHLCVCacheService,
    clear_cache,
    get_cached_ohlcv,
    get_latest_fetched_at,
    get_latest_timestamp,
    upsert_ohlcv,
)


def _make_candles(n: int, start: datetime | None = None) -> list[OHLCVData]:
    base = start or datetime(2024, 1, 1, tzinfo=UTC)
    return [
        OHLCVData(
            timestamp=base + timedelta(hours=i),
            open=100.0 + i,
            high=102.0 + i,
            low=99.0 + i,
            close=101.0 + i,
            volume=1000.0 + i * 10,
        )
        for i in range(n)
    ]


@pytest.mark.integration
class TestOHLCVCache:
    async def test_upsert_and_read(self, db_session):
        candles = _make_candles(5)
        count = await upsert_ohlcv(db_session, "EURUSD", "H1", candles)
        assert count == 5

        cached = await get_cached_ohlcv(db_session, "EURUSD", "H1")
        assert len(cached) == 5
        assert cached[0].open == 100.0
        assert cached[-1].close == 105.0

    async def test_get_latest_timestamp(self, db_session):
        candles = _make_candles(3)
        await upsert_ohlcv(db_session, "EURUSD", "H1", candles)

        latest = await get_latest_timestamp(db_session, "EURUSD", "H1")
        # SQLite strips tzinfo — compare naive datetimes
        expected = candles[-1].timestamp.replace(tzinfo=None)
        assert latest == expected

    async def test_get_latest_timestamp_empty(self, db_session):
        latest = await get_latest_timestamp(db_session, "GBPUSD", "H1")
        assert latest is None

    async def test_upsert_replaces_existing(self, db_session):
        candles = _make_candles(3)
        await upsert_ohlcv(db_session, "EURUSD", "H1", candles)

        # Update the same timestamps with new data
        updated = [
            OHLCVData(
                timestamp=c.timestamp,
                open=c.open + 10,
                high=c.high + 10,
                low=c.low + 10,
                close=c.close + 10,
                volume=c.volume,
            )
            for c in candles
        ]
        await upsert_ohlcv(db_session, "EURUSD", "H1", updated)

        cached = await get_cached_ohlcv(db_session, "EURUSD", "H1")
        assert len(cached) == 3
        assert cached[0].open == 110.0

    async def test_clear_cache(self, db_session):
        await upsert_ohlcv(db_session, "EURUSD", "H1", _make_candles(5))
        await clear_cache(db_session, "EURUSD", "H1")

        cached = await get_cached_ohlcv(db_session, "EURUSD", "H1")
        assert len(cached) == 0

    async def test_isolation_between_symbols(self, db_session):
        await upsert_ohlcv(db_session, "EURUSD", "H1", _make_candles(3))
        await upsert_ohlcv(db_session, "GBPUSD", "H1", _make_candles(2))

        eur = await get_cached_ohlcv(db_session, "EURUSD", "H1")
        gbp = await get_cached_ohlcv(db_session, "GBPUSD", "H1")
        assert len(eur) == 3
        assert len(gbp) == 2

    async def test_upsert_empty_list(self, db_session):
        count = await upsert_ohlcv(db_session, "EURUSD", "H1", [])
        assert count == 0

    async def test_get_latest_fetched_at(self, db_session):
        candles = _make_candles(3)
        await upsert_ohlcv(db_session, "EURUSD", "H1", candles)

        fetched_at = await get_latest_fetched_at(db_session, "EURUSD", "H1")
        assert fetched_at is not None

    async def test_get_latest_fetched_at_empty(self, db_session):
        fetched_at = await get_latest_fetched_at(db_session, "XAUUSD", "D1")
        assert fetched_at is None

    async def test_bulk_upsert_large_dataset(self, db_session):
        """Verify upsert handles datasets larger than chunk size."""
        candles = _make_candles(1200)  # > _UPSERT_CHUNK_SIZE (500)
        count = await upsert_ohlcv(db_session, "EURUSD", "H1", candles)
        assert count == 1200

        cached = await get_cached_ohlcv(db_session, "EURUSD", "H1")
        assert len(cached) == 1200
        # Verify ordering preserved
        assert cached[0].open == 100.0
        assert cached[-1].close == pytest.approx(101.0 + 1199)

    async def test_bulk_upsert_mixed_insert_update(self, db_session):
        """Verify upsert correctly updates existing and inserts new candles in one call."""
        initial = _make_candles(5)
        await upsert_ohlcv(db_session, "EURUSD", "H1", initial)

        # 3 updated (same timestamps) + 5 new
        mixed = [
            OHLCVData(
                timestamp=c.timestamp,
                open=c.open + 50,
                high=c.high + 50,
                low=c.low + 50,
                close=c.close + 50,
                volume=c.volume,
            )
            for c in initial[:3]
        ] + _make_candles(5, start=initial[-1].timestamp + timedelta(hours=1))

        count = await upsert_ohlcv(db_session, "EURUSD", "H1", mixed)
        assert count == 8

        cached = await get_cached_ohlcv(db_session, "EURUSD", "H1")
        assert len(cached) == 10  # 5 original (3 updated + 2 untouched) + 5 new
        # Verify updated values
        assert cached[0].open == initial[0].open + 50


@pytest.mark.integration
class TestOHLCVCacheService:
    async def test_cache_miss_fetches_from_chain(self, db_session):
        """Empty DB triggers full fetch via fetch_fn."""
        candles = _make_candles(5)
        fetch_fn = AsyncMock(return_value=candles)

        service = OHLCVCacheService(db_session)
        result = await service.get_ohlcv("EURUSD", "H1", "200d", fetch_fn)

        fetch_fn.assert_called_once_with("EURUSD", "H1", "200d")
        assert len(result) == 5

        # Data should be persisted in cache
        cached = await get_cached_ohlcv(db_session, "EURUSD", "H1")
        assert len(cached) == 5

    async def test_cache_hit_does_delta_fetch(self, db_session):
        """Data in DB + fresh fetched_at triggers delta fetch via fetch_fn."""
        candles = _make_candles(5)
        await upsert_ohlcv(db_session, "EURUSD", "D1", candles)

        # D1 is not intraday, so staleness check is skipped
        fetch_fn = AsyncMock(return_value=candles)
        service = OHLCVCacheService(db_session)
        result = await service.get_ohlcv("EURUSD", "D1", "200d", fetch_fn)

        # Delta fetch still called, but only delta is upserted
        assert len(result) == 5
        fetch_fn.assert_called_once()

    async def test_delta_fetch_appends_new_candles(self, db_session):
        """Partial data in DB, new candles from provider are appended."""
        initial = _make_candles(3)
        await upsert_ohlcv(db_session, "EURUSD", "D1", initial)

        # Provider returns 5 candles (3 existing + 2 new)
        all_candles = _make_candles(5)
        fetch_fn = AsyncMock(return_value=all_candles)

        service = OHLCVCacheService(db_session)
        result = await service.get_ohlcv("EURUSD", "D1", "200d", fetch_fn)

        assert len(result) == 5
        # Verify all candles are in the cache
        cached = await get_cached_ohlcv(db_session, "EURUSD", "D1")
        assert len(cached) == 5

    async def test_upsert_updates_existing_candle(self, db_session):
        """Cache service updates an unclosed candle with new data."""
        candles = _make_candles(3)
        await upsert_ohlcv(db_session, "EURUSD", "D1", candles)

        # Provider returns same timestamps but updated close prices
        updated = [
            OHLCVData(
                timestamp=c.timestamp,
                open=c.open,
                high=c.high + 5,
                low=c.low,
                close=c.close + 5,
                volume=c.volume,
            )
            for c in candles
        ]
        fetch_fn = AsyncMock(return_value=updated)

        service = OHLCVCacheService(db_session)
        result = await service.get_ohlcv("EURUSD", "D1", "200d", fetch_fn)

        assert len(result) == 3
        # Verify updated values
        assert result[-1].close == candles[-1].close + 5

    async def test_stale_intraday_triggers_refetch(self, db_session):
        """Intraday timeframe with stale fetched_at triggers full re-fetch."""
        candles = _make_candles(5)
        await upsert_ohlcv(db_session, "EURUSD", "H1", candles)

        fresh_candles = _make_candles(6)  # Provider returns 6 candles
        fetch_fn = AsyncMock(return_value=fresh_candles)

        # Patch _is_stale to return True (simulates stale fetched_at)
        with patch("app.modules.data_acquisition.ohlcv_cache._is_stale", return_value=True):
            service = OHLCVCacheService(db_session)
            result = await service.get_ohlcv("EURUSD", "H1", "200d", fetch_fn)

        fetch_fn.assert_called_once_with("EURUSD", "H1", "200d")
        assert len(result) == 6

    async def test_delta_fetch_exception_returns_cached(self, db_session):
        """When fetch_fn raises during delta fetch, cached data is returned."""
        candles = _make_candles(5)
        await upsert_ohlcv(db_session, "EURUSD", "D1", candles)

        fetch_fn = AsyncMock(side_effect=Exception("network error"))

        service = OHLCVCacheService(db_session)
        result = await service.get_ohlcv("EURUSD", "D1", "200d", fetch_fn)

        fetch_fn.assert_called_once()
        assert len(result) == 5
        assert result[0].open == 100.0

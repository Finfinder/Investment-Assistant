import time

from app.modules.data_acquisition.cache import InMemoryCache, make_cache_key


class TestInMemoryCache:
    def test_cache_hit(self) -> None:
        cache = InMemoryCache(default_ttl=60)
        cache.set("key1", [1, 2, 3])
        assert cache.get("key1") == [1, 2, 3]

    def test_cache_miss(self) -> None:
        cache = InMemoryCache(default_ttl=60)
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self) -> None:
        cache = InMemoryCache(default_ttl=1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_invalidate(self) -> None:
        cache = InMemoryCache(default_ttl=60)
        cache.set("key1", "value1")
        cache.invalidate("key1")
        assert cache.get("key1") is None

    def test_invalidate_nonexistent(self) -> None:
        cache = InMemoryCache(default_ttl=60)
        cache.invalidate("nonexistent")  # Should not raise


class TestMakeCacheKey:
    def test_key_format(self) -> None:
        key = make_cache_key("EURUSD", "H1", "30d")
        assert key == "ohlcv:EURUSD:H1:30d"

    def test_key_uppercased(self) -> None:
        key = make_cache_key("eurusd", "H1", "30d")
        assert key == "ohlcv:EURUSD:H1:30d"

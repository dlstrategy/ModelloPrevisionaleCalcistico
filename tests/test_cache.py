from src.sportmonks.cache import ResponseCache


def test_cache_set_and_get():
    cache = ResponseCache(":memory:")
    try:
        key = ResponseCache.make_key("/fixtures/date/2025-01-01", {"include": "participants"})
        payload = {"data": [{"id": 1}]}
        cache.set(key, payload, ttl_seconds=3600)
        assert cache.get(key) == payload
    finally:
        cache.close()


def test_cache_expired_returns_none():
    cache = ResponseCache(":memory:")
    try:
        key = "expired-key"
        cache.set(key, {"data": []}, ttl_seconds=0)
        import time
        time.sleep(0.01)
        assert cache.get(key) is None
    finally:
        cache.close()

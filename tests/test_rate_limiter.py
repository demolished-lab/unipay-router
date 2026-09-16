from unipay_router.rate_limiter import InMemoryRateLimiter


def test_in_memory_limiter_allows_until_limit_then_blocks():
    limiter = InMemoryRateLimiter(limit=2, window_seconds=10)
    first = limiter.check("client", now=100.0)
    second = limiter.check("client", now=101.0)
    blocked = limiter.check("client", now=102.0)

    assert first.allowed is True
    assert first.remaining == 1
    assert second.allowed is True
    assert second.remaining == 0
    assert blocked.allowed is False
    assert blocked.retry_after > 0
    assert blocked.remaining == 0


def test_in_memory_limiter_expires_old_events():
    limiter = InMemoryRateLimiter(limit=1, window_seconds=10)
    assert limiter.check("client", now=100.0).allowed
    assert not limiter.check("client", now=105.0).allowed
    assert limiter.check("client", now=110.1).allowed


def test_clients_have_independent_buckets():
    limiter = InMemoryRateLimiter(limit=1, window_seconds=10)
    assert limiter.check("one", now=100.0).allowed
    assert limiter.check("two", now=100.0).allowed

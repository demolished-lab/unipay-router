"""Rate limiting backends for the UniPay HTTP server."""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    reset_at: int
    retry_after: int = 0


class InMemoryRateLimiter:
    """Sliding-window limiter suitable for one process or local development."""

    def __init__(self, limit: int = 100, window_seconds: int = 60) -> None:
        self.limit = max(1, limit)
        self.window_seconds = max(1, window_seconds)
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> RateLimitDecision:
        current = time.time() if now is None else now
        cutoff = current - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            reset_at = int((events[0] if events else current) + self.window_seconds)
            if len(events) >= self.limit:
                retry_after = max(1, int(events[0] + self.window_seconds - current + 0.999))
                return RateLimitDecision(False, self.limit, 0, reset_at, retry_after)
            events.append(current)
            return RateLimitDecision(True, self.limit, self.limit - len(events), reset_at)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


class RedisRateLimiter:
    """Fixed-window Redis limiter using atomic INCR and EXPIRE operations."""

    def __init__(self, url: str, limit: int = 100, window_seconds: int = 60) -> None:
        if urlparse(url).scheme not in {"redis", "rediss"}:
            raise ValueError("REDIS_URL must use redis:// or rediss://")
        try:
            import redis
        except ImportError as exc:  # pragma: no cover - depends on optional deployment extra
            raise RuntimeError("Install the redis optional dependency to use Redis rate limiting") from exc
        self.client = redis.Redis.from_url(url, decode_responses=True)
        self.limit = max(1, limit)
        self.window_seconds = max(1, window_seconds)

    def check(self, key: str, now: float | None = None) -> RateLimitDecision:
        current = time.time() if now is None else now
        window = int(current // self.window_seconds)
        redis_key = f"unipay:ratelimit:{key}:{window}"
        count = int(self.client.incr(redis_key))
        if count == 1:
            self.client.expire(redis_key, self.window_seconds + 1)
        reset_at = (window + 1) * self.window_seconds
        allowed = count <= self.limit
        remaining = max(0, self.limit - count)
        retry_after = max(1, int(reset_at - current + 0.999)) if not allowed else 0
        return RateLimitDecision(allowed, self.limit, remaining, reset_at, retry_after)


def build_rate_limiter() -> InMemoryRateLimiter | RedisRateLimiter:
    """Build the configured backend, defaulting to the free in-memory backend."""
    limit = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    window = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    backend = os.getenv("RATE_LIMIT_BACKEND", "memory").lower()
    if backend == "redis":
        return RedisRateLimiter(os.getenv("REDIS_URL", "redis://redis:6379/0"), limit, window)
    return InMemoryRateLimiter(limit, window)

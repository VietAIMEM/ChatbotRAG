from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    """Sliding-window rate limiter backed by in-memory timestamps."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        if limit <= 0:
            return True, 0
        now = time.monotonic()
        async with self._lock:
            queue = self._hits[key]
            while queue and queue[0] < now - window_seconds:
                queue.popleft()
            if len(queue) >= limit:
                retry_after = max(1, int(window_seconds - (now - queue[0])) + 1)
                return False, retry_after
            queue.append(now)
            return True, 0

    def reset(self, key: str | None = None) -> None:
        if key:
            self._hits.pop(key, None)
        else:
            self._hits.clear()


chat_rate_limiter = InMemoryRateLimiter()
admin_login_rate_limiter = InMemoryRateLimiter()

from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass(frozen=True, slots=True)
class RateLimit:
    requests: int = 2
    period: float = 1.0

    def __post_init__(self) -> None:
        if self.requests < 1 or self.period <= 0:
            raise ValueError("RateLimit requires requests >= 1 and period > 0")


class SyncRateLimiter:
    def __init__(
        self,
        limit: RateLimit,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.limit = limit
        self._clock = clock
        self._sleep = sleep
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = self._clock()
            while self._timestamps and now - self._timestamps[0] >= self.limit.period:
                self._timestamps.popleft()
            if len(self._timestamps) >= self.limit.requests:
                self._sleep(max(0.0, self.limit.period - (now - self._timestamps[0])))
                now = self._clock()
                while self._timestamps and now - self._timestamps[0] >= self.limit.period:
                    self._timestamps.popleft()
            self._timestamps.append(self._clock())


class AsyncRateLimiter:
    def __init__(
        self,
        limit: RateLimit,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.limit = limit
        self._clock = clock
        self._sleep = sleep
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = self._clock()
            while self._timestamps and now - self._timestamps[0] >= self.limit.period:
                self._timestamps.popleft()
            if len(self._timestamps) >= self.limit.requests:
                await self._sleep(max(0.0, self.limit.period - (now - self._timestamps[0])))
                now = self._clock()
                while self._timestamps and now - self._timestamps[0] >= self.limit.period:
                    self._timestamps.popleft()
            self._timestamps.append(self._clock())

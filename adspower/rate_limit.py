from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Awaitable, Callable

EndpointLimitKey = str | tuple[str, str]


@dataclass(frozen=True, slots=True)
class RateLimit:
    """A rolling-window client-side request budget."""

    requests: int = 2
    period: float = 1.0

    def __post_init__(self) -> None:
        if self.requests < 1 or self.period <= 0:
            raise ValueError("RateLimit requires requests >= 1 and period > 0")


@dataclass(frozen=True, slots=True)
class AdsPowerRatePolicy:
    """AdsPower-specific client-side limits derived from documented public limits.

    This policy is a compliance guard only. AdsPower does not document its
    internal server-side window/token-bucket algorithm, and separate SDK clients
    or processes do not coordinate their in-memory budgets.
    """

    global_limit: RateLimit
    endpoint_limits: Mapping[EndpointLimitKey, RateLimit] = field(default_factory=dict)

    @classmethod
    def conservative(cls) -> "AdsPowerRatePolicy":
        """Return the documented lowest global tier plus verified endpoint exceptions."""
        return cls(
            global_limit=RateLimit(2, 1.0),
            endpoint_limits={"/api/v2/browser-profile/cookies": RateLimit(1, 1.0)},
        )

    @classmethod
    def for_profile_count(cls, profile_count: int) -> "AdsPowerRatePolicy":
        """Build the documented 2/5/10 requests-per-second tier for a profile count."""
        if profile_count < 0:
            raise ValueError("profile_count must be >= 0")
        requests = 2 if profile_count <= 200 else 5 if profile_count <= 5000 else 10
        return cls(
            global_limit=RateLimit(requests, 1.0),
            endpoint_limits={"/api/v2/browser-profile/cookies": RateLimit(1, 1.0)},
        )


class SyncRateLimiter:
    """Thread-safe rolling-window limiter for synchronous clients."""

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
    """Coroutine-safe rolling-window limiter for asynchronous clients."""

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

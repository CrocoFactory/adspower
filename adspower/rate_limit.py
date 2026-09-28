from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from .errors import AdsPowerConfigurationError

EndpointLimitKey = str | tuple[str, str]


@dataclass(frozen=True, slots=True)
class RateLimit:
    requests: int = 2
    period: float = 1.0

    def __post_init__(self) -> None:
        if self.requests < 1 or self.period <= 0:
            raise ValueError("RateLimit requires requests >= 1 and period > 0")


@dataclass(frozen=True, slots=True)
class AdsPowerRatePolicy:
    """Client-side compliance limits; not AdsPower's undisclosed server algorithm."""

    global_limit: RateLimit
    endpoint_limits: Mapping[EndpointLimitKey, RateLimit] = field(default_factory=dict)

    @classmethod
    def conservative(cls) -> "AdsPowerRatePolicy":
        return cls(global_limit=RateLimit(2, 1.0), endpoint_limits=_restricted_endpoint_limits())

    @classmethod
    def for_profile_count(cls, profile_count: int) -> "AdsPowerRatePolicy":
        if profile_count < 0:
            raise ValueError("profile_count must be >= 0")
        requests = 2 if profile_count <= 200 else 5 if profile_count <= 5000 else 10
        return cls(global_limit=RateLimit(requests, 1.0), endpoint_limits=_restricted_endpoint_limits())


def _restricted_endpoint_limits() -> dict[EndpointLimitKey, RateLimit]:
    """Return the documented one-request-per-second Local API limits."""
    limit = RateLimit(1, 1.0)
    return {
        ("GET", "/api/v1/group/list"): limit,
        ("POST", "/api/v2/browser-profile/list"): limit,
        ("GET", "/api/v2/browser-profile/cookies"): limit,
        ("POST", "/api/v2/browser-profile/ua"): limit,
    }


def _normalize_limits(
    limits: Mapping[EndpointLimitKey, RateLimit] | None,
) -> dict[tuple[str | None, str], RateLimit]:
    result: dict[tuple[str | None, str], RateLimit] = {}
    for key, limit in (limits or {}).items():
        if isinstance(key, tuple):
            if len(key) != 2:
                raise AdsPowerConfigurationError("endpoint limit tuple must be (method, path)")
            method, path = key
            result[(method.upper(), path)] = limit
        else:
            result[(None, key)] = limit
    return result


class _Budget:
    def __init__(self, limit: RateLimit) -> None:
        self.limit = limit
        self.timestamps: deque[float] = deque()

    def prune(self, now: float) -> None:
        while self.timestamps and now - self.timestamps[0] >= self.limit.period:
            self.timestamps.popleft()

    def wait(self, now: float) -> float:
        self.prune(now)
        if len(self.timestamps) < self.limit.requests:
            return 0.0
        return max(0.0, self.limit.period - (now - self.timestamps[0]))

    def reserve(self, now: float) -> None:
        self.prune(now)
        self.timestamps.append(now)


class SyncRateLimiter:
    """Atomically reserve global and endpoint budgets at dispatch time."""

    def __init__(
        self,
        global_limit: RateLimit | None,
        endpoint_limits: Mapping[EndpointLimitKey, RateLimit] | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._global = _Budget(global_limit) if global_limit else None
        self._endpoints = {key: _Budget(limit) for key, limit in _normalize_limits(endpoint_limits).items()}
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()

    def acquire(self, method: str, path: str) -> None:
        with self._lock:
            endpoint = self._endpoints.get((method.upper(), path)) or self._endpoints.get((None, path))
            budgets = [budget for budget in (self._global, endpoint) if budget is not None]
            if not budgets:
                return
            now = self._clock()
            delay = max((budget.wait(now) for budget in budgets), default=0.0)
            if delay:
                self._sleep(delay)
                now = self._clock()
            for budget in budgets:
                budget.reserve(now)


class AsyncRateLimiter:
    """Async equivalent of SyncRateLimiter with identical reservation semantics."""

    def __init__(
        self,
        global_limit: RateLimit | None,
        endpoint_limits: Mapping[EndpointLimitKey, RateLimit] | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._global = _Budget(global_limit) if global_limit else None
        self._endpoints = {key: _Budget(limit) for key, limit in _normalize_limits(endpoint_limits).items()}
        self._clock = clock
        self._sleep = sleep
        self._lock = asyncio.Lock()

    async def acquire(self, method: str, path: str) -> None:
        async with self._lock:
            endpoint = self._endpoints.get((method.upper(), path)) or self._endpoints.get((None, path))
            budgets = [budget for budget in (self._global, endpoint) if budget is not None]
            if not budgets:
                return
            now = self._clock()
            delay = max((budget.wait(now) for budget in budgets), default=0.0)
            if delay:
                await self._sleep(delay)
                now = self._clock()
            for budget in budgets:
                budget.reserve(now)

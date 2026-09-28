from __future__ import annotations

import pytest

from adspower import AdsPowerRatePolicy, RateLimit
from adspower._security import redact_sensitive, redact_url_credentials
from adspower.rate_limit import AsyncRateLimiter, SyncRateLimiter


class Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)
        self.now += delay

    async def asleep(self, delay: float) -> None:
        self.sleep(delay)


def test_rate_limit_value_and_policy_validation() -> None:
    with pytest.raises(ValueError):
        RateLimit(0, 1)
    with pytest.raises(ValueError):
        RateLimit(1, 0)
    assert AdsPowerRatePolicy.for_profile_count(200).global_limit.requests == 2
    assert AdsPowerRatePolicy.for_profile_count(201).global_limit.requests == 5
    assert AdsPowerRatePolicy.for_profile_count(5001).global_limit.requests == 10
    policy = AdsPowerRatePolicy.for_profile_count(0)
    assert policy.endpoint_limits[("GET", "/api/v1/group/list")] == RateLimit(1, 1)
    assert policy.endpoint_limits[("POST", "/api/v2/browser-profile/list")] == RateLimit(1, 1)
    assert policy.endpoint_limits[("GET", "/api/v2/browser-profile/cookies")] == RateLimit(1, 1)
    assert policy.endpoint_limits[("POST", "/api/v2/browser-profile/ua")] == RateLimit(1, 1)


def test_sync_composite_limiter_waits_once_and_reserves_together() -> None:
    clock = Clock()
    limiter = SyncRateLimiter(
        RateLimit(2, 1),
        {("GET", "/slow"): RateLimit(1, 1)},
        clock=clock,
        sleep=clock.sleep,
    )
    limiter.acquire("GET", "/slow")
    limiter.acquire("GET", "/slow")
    assert clock.sleeps == [1.0]
    limiter.acquire("GET", "/other")
    assert clock.sleeps == [1.0]


@pytest.mark.asyncio
async def test_async_composite_limiter_matches_sync_semantics() -> None:
    clock = Clock()
    limiter = AsyncRateLimiter(
        RateLimit(2, 1),
        {"/slow": RateLimit(1, 1)},
        clock=clock,
        sleep=clock.asleep,
    )
    await limiter.acquire("POST", "/slow")
    await limiter.acquire("POST", "/slow")
    assert clock.sleeps == [1.0]


def test_redaction_covers_nested_secrets_and_proxy_urls() -> None:
    value = {
        "password": "p",
        "nested": {"fakey": "f", "cookie": "c"},
        "ok": "visible",
        "proxy_url": "http://user:pass@example.test",
    }
    redacted = redact_sensitive(value)
    assert redacted["password"] == "<redacted>"
    assert redacted["nested"]["fakey"] == "<redacted>"
    assert redacted["ok"] == "visible"
    assert redact_url_credentials("http://user:pass@example.test:8080/path") == (
        "http://<redacted>@example.test:8080/path"
    )

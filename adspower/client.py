from __future__ import annotations

from collections.abc import Mapping
from typing import Self

import httpx

from .config import AdsPowerConfig, BrowserEndpointPolicy
from .errors import AdsPowerValidationError
from .rate_limit import AdsPowerRatePolicy, EndpointLimitKey, RateLimit
from .resources import (
    AppResource,
    BrowsersResource,
    CategoriesResource,
    GroupsResource,
    HealthResource,
    KernelsResource,
    ProfilesResource,
    ProxiesResource,
    RawResource,
    TagsResource,
)
from .transport import SyncTransport


class AdsPowerClient:
    """Synchronous AdsPower Local API client."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: httpx.Timeout | float | None = None,
        browser_start_timeout: float | None = None,
        browser_probe_timeout: float | None = None,
        browser_host: str | None = None,
        browser_endpoint_policy: BrowserEndpointPolicy | None = None,
        rate_limit: RateLimit | None = None,
        endpoint_limits: Mapping[EndpointLimitKey, RateLimit] | None = None,
        rate_policy: AdsPowerRatePolicy | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if rate_policy is not None and (rate_limit is not None or endpoint_limits is not None):
            raise AdsPowerValidationError("rate_policy is mutually exclusive with explicit limits")
        if rate_policy is not None:
            rate_limit = rate_policy.global_limit
            endpoint_limits = rate_policy.endpoint_limits
        self.config = AdsPowerConfig.resolve(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            browser_start_timeout=browser_start_timeout,
            browser_probe_timeout=browser_probe_timeout,
            browser_host=browser_host,
            browser_endpoint_policy=browser_endpoint_policy,
        )
        self._transport = SyncTransport(
            self.config,
            rate_limit=rate_limit,
            endpoint_limits=endpoint_limits,
            transport=transport,
        )
        self.profiles = ProfilesResource(self._transport)
        self.browsers = BrowsersResource(self._transport, self.config)
        self.groups = GroupsResource(self._transport)
        self.proxies = ProxiesResource(self._transport)
        self.categories = CategoriesResource(self._transport)
        self.tags = TagsResource(self._transport)
        self.kernels = KernelsResource(self._transport)
        self.app = AppResource(self._transport)
        self.health = HealthResource(self._transport)
        self.raw = RawResource(self._transport)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"AdsPowerClient(base_url={self.config.base_url!r}, api_key=<redacted>)"

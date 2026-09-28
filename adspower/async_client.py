from __future__ import annotations

from collections.abc import Mapping
from typing import Self

import httpx

from .config import AdsPowerConfig, BrowserEndpointPolicy
from .errors import AdsPowerValidationError
from .rate_limit import AdsPowerRatePolicy, EndpointLimitKey, RateLimit
from .resources import (
    AsyncAppResource,
    AsyncBrowsersResource,
    AsyncCategoriesResource,
    AsyncGroupsResource,
    AsyncHealthResource,
    AsyncKernelsResource,
    AsyncProfilesResource,
    AsyncProxiesResource,
    AsyncRawResource,
    AsyncTagsResource,
)
from .transport import AsyncTransport


class AsyncAdsPowerClient:
    """Asynchronous AdsPower Local API client with the same namespaces as the sync client."""

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
        transport: httpx.AsyncBaseTransport | None = None,
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
        self._transport = AsyncTransport(
            self.config,
            rate_limit=rate_limit,
            endpoint_limits=endpoint_limits,
            transport=transport,
        )
        self.profiles = AsyncProfilesResource(self._transport)
        self.browsers = AsyncBrowsersResource(self._transport, self.config)
        self.groups = AsyncGroupsResource(self._transport)
        self.proxies = AsyncProxiesResource(self._transport)
        self.categories = AsyncCategoriesResource(self._transport)
        self.tags = AsyncTagsResource(self._transport)
        self.kernels = AsyncKernelsResource(self._transport)
        self.app = AsyncAppResource(self._transport)
        self.health = AsyncHealthResource(self._transport)
        self.raw = AsyncRawResource(self._transport)

    async def close(self) -> None:
        await self._transport.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    def __repr__(self) -> str:
        return f"AsyncAdsPowerClient(base_url={self.config.base_url!r}, api_key=<redacted>)"

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from .api import AsyncGroupsAPI, AsyncHealthAPI, AsyncProfilesAPI, parse_browser_connection
from .automation import AsyncPlaywrightSession
from .config import ClientConfig
from .models import BrowserConnection
from .rate_limit import RateLimit
from .transport import AsyncTransport


class AsyncBrowserSession:
    def __init__(self, profile_id: str, connection: BrowserConnection, api: "AsyncBrowsersAPI") -> None:
        self.profile_id = profile_id
        self.connection = connection
        self._api = api
        self._stopped = False

    async def stop(self) -> None:
        if not self._stopped:
            await self._api.stop(self.profile_id)
            self._stopped = True

    def playwright(self, *, stop_on_exit: bool = True) -> AsyncPlaywrightSession:
        return AsyncPlaywrightSession(self.connection, stop=self.stop, stop_on_exit=stop_on_exit)


class AsyncBrowsersAPI:
    def __init__(self, transport: AsyncTransport, config: ClientConfig) -> None:
        self._transport = transport
        self._config = config

    async def start(self, profile_id: str, *, headless: bool = False, timeout: float | None = None, **options: Any) -> AsyncBrowserSession:
        payload = {"profile_id": profile_id, "headless": "1" if headless else "0", **options}
        data = await self._transport.request(
            "POST",
            "/api/v2/browser-profile/start",
            json=payload,
            timeout=timeout or self._config.browser_start_timeout,
        )
        return AsyncBrowserSession(profile_id, parse_browser_connection(data, self._config.base_url), self)

    async def stop(self, profile_id: str) -> None:
        await self._transport.request("POST", "/api/v2/browser-profile/stop", json={"profile_id": profile_id})


class AsyncAdsPowerClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: httpx.Timeout | float | None = None,
        browser_start_timeout: float = 60.0,
        rate_limit: RateLimit | None = None,
        endpoint_limits: Mapping[str, RateLimit] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = ClientConfig.resolve(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            browser_start_timeout=browser_start_timeout,
        )
        self._transport = AsyncTransport(
            self.config,
            rate_limit=rate_limit,
            endpoint_limits=endpoint_limits,
            transport=transport,
        )
        self.profiles = AsyncProfilesAPI(self._transport)
        self.groups = AsyncGroupsAPI(self._transport)
        self.browsers = AsyncBrowsersAPI(self._transport, self.config)
        self.health = AsyncHealthAPI(self._transport)

    async def close(self) -> None:
        await self._transport.close()

    async def __aenter__(self) -> "AsyncAdsPowerClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    def __repr__(self) -> str:
        return f"AsyncAdsPowerClient(base_url={self.config.base_url!r}, api_key=<redacted>)"

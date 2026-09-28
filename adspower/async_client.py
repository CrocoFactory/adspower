from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from .api import (
    AsyncCategoriesAPI,
    AsyncGroupsAPI,
    AsyncHealthAPI,
    AsyncProfilesAPI,
    AsyncProxiesAPI,
    parse_browser_connection,
    parse_browser_status,
    parse_running_browsers,
)
from .automation import AsyncPlaywrightSession
from .config import ClientConfig
from .models import BrowserConnection, BrowserStatus, ProfileSelector, RunningBrowser
from .rate_limit import RateLimit
from .transport import AsyncTransport


class AsyncBrowserSession:
    def __init__(self, selector: ProfileSelector, connection: BrowserConnection, api: "AsyncBrowsersAPI") -> None:
        self.profile_id = selector.profile_id
        self.profile_no = selector.profile_no
        self.selector = selector
        self.connection = connection
        self._api = api
        self._stopped = False

    async def stop(self) -> None:
        if not self._stopped:
            await self._api.stop(self.profile_id, profile_no=self.profile_no)
            self._stopped = True

    def playwright(self, *, stop_on_exit: bool = True, timeout: float | None = None, slow_mo: float | None = None, headers: Mapping[str, str] | None = None, is_local: bool | None = None, no_defaults: bool = True, artifacts_dir: str | None = None, connect_kwargs: Mapping[str, Any] | None = None) -> AsyncPlaywrightSession:
        return AsyncPlaywrightSession(self.connection, stop=self.stop, stop_on_exit=stop_on_exit, timeout=timeout, slow_mo=slow_mo, headers=headers, is_local=is_local, no_defaults=no_defaults, artifacts_dir=artifacts_dir, connect_kwargs=connect_kwargs)


class AsyncBrowsersAPI:
    def __init__(self, transport: AsyncTransport, config: ClientConfig) -> None:
        self._transport = transport
        self._config = config

    async def start(self, profile_id: str | None = None, *, profile_no: str | None = None, headless: bool = False, start_maximized: bool = False, timeout: float | None = None, **options: Any) -> AsyncBrowserSession:
        selector = ProfileSelector(profile_id=profile_id, profile_no=profile_no)
        raw_launch_args = options.pop("launch_args", []) or []
        if isinstance(raw_launch_args, (str, bytes)):
            raise ValueError("launch_args must be a sequence of arguments, not a string")
        launch_args = list(raw_launch_args)
        if not any(str(arg).startswith("--window-size=") for arg in launch_args) and "--start-maximized" not in launch_args and start_maximized:
            launch_args.append("--start-maximized")
        if launch_args:
            options["launch_args"] = launch_args
        payload = {**selector.payload, "headless": "1" if headless else "0", **options}
        effective_timeout = self._config.browser_start_timeout if timeout is None else timeout
        data = await self._transport.request(
            "POST",
            "/api/v2/browser-profile/start",
            json=payload,
            timeout=effective_timeout,
        )
        return AsyncBrowserSession(selector, parse_browser_connection(data, self._config.base_url), self)

    async def stop(self, profile_id: str | None = None, *, profile_no: str | None = None) -> None:
        await self._transport.request("POST", "/api/v2/browser-profile/stop", json=ProfileSelector(profile_id=profile_id, profile_no=profile_no).payload)

    async def status(self, profile_id: str | None = None, *, profile_no: str | None = None) -> BrowserStatus:
        selector = ProfileSelector(profile_id=profile_id, profile_no=profile_no)
        data = await self._transport.request("GET", "/api/v2/browser-profile/active", params=selector.payload)
        return parse_browser_status(data, self._config.base_url)

    async def list_active(self) -> list[RunningBrowser]:
        data = await self._transport.request("GET", "/api/v1/browser/local-active")
        return parse_running_browsers(data, self._config.base_url)


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
        self.proxies = AsyncProxiesAPI(self._transport)
        self.categories = AsyncCategoriesAPI(self._transport)
        self.health = AsyncHealthAPI(self._transport)

    async def request(self, method: str, path: str, *, params: Mapping[str, Any] | None = None, json: Any = None, timeout: float | httpx.Timeout | None = None, unwrap: bool = True) -> Any:
        from urllib.parse import urlsplit
        parsed = urlsplit(path)
        if parsed.scheme or parsed.netloc or not path.startswith("/"):
            raise ValueError("AdsPower raw requests require an absolute relative path")
        return await self._transport.request(method, path, params=params, json=json, timeout=timeout, unwrap=unwrap)

    async def close(self) -> None:
        await self._transport.close()

    async def __aenter__(self) -> "AsyncAdsPowerClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    def __repr__(self) -> str:
        return f"AsyncAdsPowerClient(base_url={self.config.base_url!r}, api_key=<redacted>)"

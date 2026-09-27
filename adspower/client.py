from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

import httpx

from .api import (
    CategoriesAPI,
    GroupsAPI,
    HealthAPI,
    ProfilesAPI,
    ProxiesAPI,
    parse_browser_connection,
    parse_browser_status,
    parse_running_browsers,
)
from .automation import PlaywrightSession, SeleniumSession
from .config import ClientConfig
from .models import BrowserConnection, BrowserStatus, ProfileSelector, RunningBrowser
from .rate_limit import RateLimit
from .transport import SyncTransport


class BrowserSession:
    def __init__(self, selector: ProfileSelector, connection: BrowserConnection, api: "BrowsersAPI") -> None:
        self.profile_id = selector.profile_id
        self.profile_no = selector.profile_no
        self.selector = selector
        self.connection = connection
        self._api = api
        self._stopped = False

    def stop(self) -> None:
        if not self._stopped:
            self._api.stop(self.profile_id, profile_no=self.profile_no)
            self._stopped = True

    def selenium(
        self,
        *,
        stop_on_exit: bool = True,
        start_maximized: bool = False,
        page_load_strategy: Literal["normal", "eager", "none"] | None = None,
        options: Any = None,
        browser: Literal["auto", "chromium", "chrome", "firefox"] = "auto",
        service: Any = None,
        service_kwargs: Mapping[str, Any] | None = None,
        webdriver_kwargs: Mapping[str, Any] | None = None,
    ) -> SeleniumSession:
        return SeleniumSession(
            self.connection,
            stop=self.stop,
            stop_on_exit=stop_on_exit,
            start_maximized=start_maximized,
            page_load_strategy=page_load_strategy,
            options=options,
            browser=browser,
            service=service,
            service_kwargs=service_kwargs,
            webdriver_kwargs=webdriver_kwargs,
        )

    def playwright(self, *, stop_on_exit: bool = True, timeout: float | None = None, slow_mo: float | None = None, headers: Mapping[str, str] | None = None, is_local: bool | None = None, no_defaults: bool | None = None, artifacts_dir: str | None = None, connect_kwargs: Mapping[str, Any] | None = None) -> PlaywrightSession:
        return PlaywrightSession(self.connection, stop=self.stop, stop_on_exit=stop_on_exit, timeout=timeout, slow_mo=slow_mo, headers=headers, is_local=is_local, no_defaults=no_defaults, artifacts_dir=artifacts_dir, connect_kwargs=connect_kwargs)


class BrowsersAPI:
    def __init__(self, transport: SyncTransport, config: ClientConfig) -> None:
        self._transport = transport
        self._config = config

    def start(self, profile_id: str | None = None, *, profile_no: str | None = None, headless: bool = False, timeout: float | None = None, **options: Any) -> BrowserSession:
        selector = ProfileSelector(profile_id=profile_id, profile_no=profile_no)
        payload = {**selector.payload, "headless": "1" if headless else "0", **options}
        effective_timeout = self._config.browser_start_timeout if timeout is None else timeout
        data = self._transport.request(
            "POST",
            "/api/v2/browser-profile/start",
            json=payload,
            timeout=effective_timeout,
        )
        return BrowserSession(selector, parse_browser_connection(data, self._config.base_url), self)

    def stop(self, profile_id: str | None = None, *, profile_no: str | None = None) -> None:
        self._transport.request("POST", "/api/v2/browser-profile/stop", json=ProfileSelector(profile_id=profile_id, profile_no=profile_no).payload)

    def status(self, profile_id: str | None = None, *, profile_no: str | None = None) -> BrowserStatus:
        selector = ProfileSelector(profile_id=profile_id, profile_no=profile_no)
        data = self._transport.request("GET", "/api/v2/browser-profile/active", params=selector.payload)
        return parse_browser_status(data, self._config.base_url)

    def list_active(self) -> list[RunningBrowser]:
        data = self._transport.request("GET", "/api/v1/browser/local-active")
        return parse_running_browsers(data, self._config.base_url)


class AdsPowerClient:
    """Synchronous AdsPower client for the current AdsPower API."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: httpx.Timeout | float | None = None,
        browser_start_timeout: float = 60.0,
        rate_limit: RateLimit | None = None,
        endpoint_limits: Mapping[str, RateLimit] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = ClientConfig.resolve(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            browser_start_timeout=browser_start_timeout,
        )
        self._transport = SyncTransport(
            self.config,
            rate_limit=rate_limit,
            endpoint_limits=endpoint_limits,
            transport=transport,
        )
        self.profiles = ProfilesAPI(self._transport)
        self.groups = GroupsAPI(self._transport)
        self.browsers = BrowsersAPI(self._transport, self.config)
        self.proxies = ProxiesAPI(self._transport)
        self.categories = CategoriesAPI(self._transport)
        self.health = HealthAPI(self._transport)

    def request(self, method: str, path: str, *, params: Mapping[str, Any] | None = None, json: Any = None, timeout: float | httpx.Timeout | None = None, unwrap: bool = True) -> Any:
        from urllib.parse import urlsplit
        parsed = urlsplit(path)
        if parsed.scheme or parsed.netloc or not path.startswith("/"):
            raise ValueError("AdsPower raw requests require an absolute relative path")
        return self._transport.request(method, path, params=params, json=json, timeout=timeout, unwrap=unwrap)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> "AdsPowerClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"AdsPowerClient(base_url={self.config.base_url!r}, api_key=<redacted>)"

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx

from .api import (
    CategoriesAPI,
    GroupsAPI,
    HealthAPI,
    ProfilesAPI,
    ProxiesAPI,
    build_browser_start_payload,
    parse_browser_connection,
    parse_browser_status,
    parse_running_browsers,
)
from .automation import PlaywrightSession, SeleniumSession
from .config import BrowserEndpointPolicy, ClientConfig
from .exceptions import AdsPowerValidationError
from .models import BrowserConnection, BrowserStatus, ProfileSelector, RunningBrowser
from .rate_limit import AdsPowerRatePolicy, EndpointLimitKey, RateLimit
from .transport import SyncTransport
from .types import AdsPowerBool


class BrowserSession:
    """A running AdsPower browser plus helpers for attaching automation clients."""

    def __init__(self, selector: ProfileSelector, connection: BrowserConnection, api: "BrowsersAPI") -> None:
        self.profile_id = selector.profile_id
        self.profile_no = selector.profile_no
        self.selector = selector
        self.connection = connection
        self._api = api
        self._stopped = False

    def stop(self) -> None:
        """Stop the AdsPower browser once; repeated calls are no-ops."""
        if not self._stopped:
            self._api.stop(self.profile_id, profile_no=self.profile_no)
            self._stopped = True

    def selenium(
        self,
        *,
        stop_on_exit: bool = True,
        page_load_strategy: Literal["normal", "eager", "none"] | None = None,
        options: Any = None,
        browser: Literal["auto", "chromium", "chrome", "firefox"] = "auto",
        service: Any = None,
        service_kwargs: Mapping[str, Any] | None = None,
        webdriver_kwargs: Mapping[str, Any] | None = None,
    ) -> SeleniumSession:
        """Attach Selenium to the browser returned by AdsPower."""
        return SeleniumSession(
            self.connection,
            stop=self.stop,
            stop_on_exit=stop_on_exit,
            page_load_strategy=page_load_strategy,
            options=options,
            browser=browser,
            service=service,
            service_kwargs=service_kwargs,
            webdriver_kwargs=webdriver_kwargs,
        )

    def playwright(
        self,
        *,
        stop_on_exit: bool = True,
        timeout: float | None = None,
        slow_mo: float | None = None,
        headers: Mapping[str, str] | None = None,
        is_local: bool | None = None,
        no_defaults: bool = True,
        artifacts_dir: str | None = None,
        connect_kwargs: Mapping[str, Any] | None = None,
    ) -> PlaywrightSession:
        """Attach sync Playwright over AdsPower's returned CDP endpoint."""
        return PlaywrightSession(
            self.connection,
            stop=self.stop,
            stop_on_exit=stop_on_exit,
            timeout=timeout,
            slow_mo=slow_mo,
            headers=headers,
            is_local=is_local,
            no_defaults=no_defaults,
            artifacts_dir=artifacts_dir,
            connect_kwargs=connect_kwargs,
        )


class BrowsersAPI:
    """Synchronous browser lifecycle operations."""

    def __init__(self, transport: SyncTransport, config: ClientConfig) -> None:
        self._transport = transport
        self._config = config

    def start(
        self,
        profile_id: str | None = None,
        *,
        profile_no: str | None = None,
        headless: bool = False,
        start_maximized: bool = False,
        timeout: float | None = None,
        launch_args: Sequence[str] | None = None,
        last_opened_tabs: bool | AdsPowerBool | None = None,
        proxy_detection: bool | AdsPowerBool | None = None,
        password_filling: bool | AdsPowerBool | None = None,
        password_saving: bool | AdsPowerBool | None = None,
        cdp_mask: bool | AdsPowerBool | None = None,
        delete_cache: bool | AdsPowerBool | None = None,
        device_scale: float | int | str | None = None,
        extra_options: Mapping[str, Any] | None = None,
    ) -> BrowserSession:
        """Start a browser with documented V2 options and return an automation session."""
        selector = ProfileSelector(profile_id=profile_id, profile_no=profile_no)
        payload = build_browser_start_payload(
            selector,
            headless=headless,
            start_maximized=start_maximized,
            launch_args=launch_args,
            last_opened_tabs=last_opened_tabs,
            proxy_detection=proxy_detection,
            password_filling=password_filling,
            password_saving=password_saving,
            cdp_mask=cdp_mask,
            delete_cache=delete_cache,
            device_scale=device_scale,
            extra_options=extra_options,
        )
        effective_timeout = self._config.browser_start_timeout if timeout is None else timeout
        data = self._transport.request(
            "POST",
            "/api/v2/browser-profile/start",
            json=payload,
            timeout=effective_timeout,
        )
        connection = parse_browser_connection(
            data,
            self._config.base_url,
            browser_host=self._config.browser_host,
            endpoint_policy=self._config.browser_endpoint_policy,
        )
        return BrowserSession(selector, connection, self)

    def stop(self, profile_id: str | None = None, *, profile_no: str | None = None) -> None:
        """Stop one browser selected by profile id or profile number."""
        self._transport.request(
            "POST",
            "/api/v2/browser-profile/stop",
            json=ProfileSelector(profile_id=profile_id, profile_no=profile_no).payload,
        )

    def status(self, profile_id: str | None = None, *, profile_no: str | None = None) -> BrowserStatus:
        """Return the current browser status for one profile."""
        selector = ProfileSelector(profile_id=profile_id, profile_no=profile_no)
        data = self._transport.request("GET", "/api/v2/browser-profile/active", params=selector.payload)
        return parse_browser_status(
            data,
            self._config.base_url,
            browser_host=self._config.browser_host,
            endpoint_policy=self._config.browser_endpoint_policy,
        )

    def list_active(self) -> list[RunningBrowser]:
        """List running local browsers visible to AdsPower."""
        data = self._transport.request("GET", "/api/v1/browser/local-active")
        return parse_running_browsers(
            data,
            self._config.base_url,
            browser_host=self._config.browser_host,
            endpoint_policy=self._config.browser_endpoint_policy,
        )


class AdsPowerClient:
    """Synchronous AdsPower Local API client with per-instance configuration."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: httpx.Timeout | float | None = None,
        browser_start_timeout: float = 60.0,
        browser_host: str | None = None,
        browser_endpoint_policy: BrowserEndpointPolicy = "rewrite_loopback_to_api_host",
        rate_limit: RateLimit | None = None,
        endpoint_limits: Mapping[EndpointLimitKey, RateLimit] | None = None,
        rate_policy: AdsPowerRatePolicy | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if rate_policy is not None and (rate_limit is not None or endpoint_limits is not None):
            raise AdsPowerValidationError(
                "rate_policy is mutually exclusive with rate_limit/endpoint_limits"
            )
        if rate_policy is not None:
            rate_limit = rate_policy.global_limit
            endpoint_limits = rate_policy.endpoint_limits

        self.config = ClientConfig.resolve(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            browser_start_timeout=browser_start_timeout,
            browser_host=browser_host,
            browser_endpoint_policy=browser_endpoint_policy,
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

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        timeout: float | httpx.Timeout | None = None,
        unwrap: bool = True,
    ) -> Any:
        """Send a raw request to a root-relative AdsPower Local API path."""
        parsed = urlsplit(path)
        if parsed.scheme or parsed.netloc or not path.startswith("/"):
            raise AdsPowerValidationError(
                "AdsPower raw requests require a root-relative AdsPower path, e.g. '/api/v2/...'"
            )
        return self._transport.request(
            method,
            path,
            params=params,
            json=json,
            timeout=timeout,
            unwrap=unwrap,
        )

    def close(self) -> None:
        """Close the underlying HTTPX client."""
        self._transport.close()

    def __enter__(self) -> "AdsPowerClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"AdsPowerClient(base_url={self.config.base_url!r}, api_key=<redacted>)"

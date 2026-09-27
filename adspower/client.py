from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

import httpx

from .api import GroupsAPI, HealthAPI, ProfilesAPI, parse_browser_connection
from .automation import PlaywrightSession, SeleniumSession
from .config import ClientConfig
from .legacy import LegacyV1
from .models import BrowserConnection
from .rate_limit import RateLimit
from .transport import SyncTransport


class BrowserSession:
    def __init__(self, profile_id: str, connection: BrowserConnection, api: "BrowsersAPI") -> None:
        self.profile_id = profile_id
        self.connection = connection
        self._api = api
        self._stopped = False

    def stop(self) -> None:
        if not self._stopped:
            self._api.stop(self.profile_id)
            self._stopped = True

    def selenium(
        self,
        *,
        stop_on_exit: bool = True,
        start_maximized: bool = False,
        page_load_strategy: Literal["normal", "eager", "none"] | None = None,
        options: Any = None,
    ) -> SeleniumSession:
        return SeleniumSession(
            self.connection,
            stop=self.stop,
            stop_on_exit=stop_on_exit,
            start_maximized=start_maximized,
            page_load_strategy=page_load_strategy,
            options=options,
        )

    def playwright(self, *, stop_on_exit: bool = True) -> PlaywrightSession:
        return PlaywrightSession(self.connection, stop=self.stop, stop_on_exit=stop_on_exit)


class BrowsersAPI:
    def __init__(self, transport: SyncTransport, config: ClientConfig) -> None:
        self._transport = transport
        self._config = config

    def start(self, profile_id: str, *, headless: bool = False, timeout: float | None = None, **options: Any) -> BrowserSession:
        payload = {"profile_id": profile_id, "headless": "1" if headless else "0", **options}
        data = self._transport.request(
            "POST",
            "/api/v2/browser-profile/start",
            json=payload,
            timeout=timeout or self._config.browser_start_timeout,
        )
        return BrowserSession(profile_id, parse_browser_connection(data, self._config.base_url), self)

    def stop(self, profile_id: str) -> None:
        self._transport.request("POST", "/api/v2/browser-profile/stop", json={"profile_id": profile_id})


class AdsPowerClient:
    """Synchronous AdsPower client. API V2 is the default; V1 is under ``client.v1``."""

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
        self.health = HealthAPI(self._transport)
        self.v1 = LegacyV1(self._transport)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> "AdsPowerClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"AdsPowerClient(base_url={self.config.base_url!r}, api_key=<redacted>)"

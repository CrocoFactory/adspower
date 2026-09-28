from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

import httpx

from .exceptions import AdsPowerConfigurationError

DEFAULT_BASE_URL = "http://127.0.0.1:50325"
BrowserEndpointPolicy = Literal["rewrite_loopback_to_api_host", "exact"]


def default_timeout() -> httpx.Timeout:
    return httpx.Timeout(connect=5.0, read=30.0, write=15.0, pool=5.0)


@dataclass(frozen=True, slots=True)
class ClientConfig:
    """Resolved, immutable client configuration."""

    base_url: str = DEFAULT_BASE_URL
    api_key: str | None = field(default=None, repr=False)
    timeout: httpx.Timeout | float = field(default_factory=default_timeout)
    browser_start_timeout: float = 60.0
    browser_host: str | None = None
    browser_endpoint_policy: BrowserEndpointPolicy = "rewrite_loopback_to_api_host"

    @classmethod
    def resolve(
        cls,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: httpx.Timeout | float | None = None,
        browser_start_timeout: float = 60.0,
        browser_host: str | None = None,
        browser_endpoint_policy: BrowserEndpointPolicy = "rewrite_loopback_to_api_host",
    ) -> "ClientConfig":
        resolved_url = base_url or os.getenv("ADSPOWER_BASE_URL") or DEFAULT_BASE_URL
        resolved_key = api_key if api_key is not None else os.getenv("ADSPOWER_API_KEY")
        resolved_browser_host = browser_host or os.getenv("ADSPOWER_BROWSER_HOST") or None
        if browser_endpoint_policy not in {"rewrite_loopback_to_api_host", "exact"}:
            raise AdsPowerConfigurationError(
                "browser_endpoint_policy must be 'rewrite_loopback_to_api_host' or 'exact'"
            )
        if resolved_browser_host is not None:
            if "://" in resolved_browser_host or "/" in resolved_browser_host:
                raise AdsPowerConfigurationError("browser_host must be a hostname or IP address without a scheme or path")
            resolved_browser_host = resolved_browser_host.strip("[]")
        return cls(
            base_url=resolved_url.rstrip("/"),
            api_key=resolved_key,
            timeout=timeout if timeout is not None else default_timeout(),
            browser_start_timeout=browser_start_timeout,
            browser_host=resolved_browser_host,
            browser_endpoint_policy=browser_endpoint_policy,
        )

    @property
    def headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}"}

    def __repr__(self) -> str:
        key = "<redacted>" if self.api_key else "None"
        return (
            f"ClientConfig(base_url={self.base_url!r}, api_key={key}, timeout={self.timeout!r}, "
            f"browser_start_timeout={self.browser_start_timeout!r}, browser_host={self.browser_host!r}, "
            f"browser_endpoint_policy={self.browser_endpoint_policy!r})"
        )

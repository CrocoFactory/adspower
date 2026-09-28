from __future__ import annotations

import ipaddress
import os
import re
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

import httpx

from .errors import AdsPowerConfigurationError

DEFAULT_BASE_URL = "http://127.0.0.1:50325"
BrowserEndpointPolicy = Literal["rewrite_loopback_to_api_host", "exact"]
_HOST_RE = re.compile(r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def default_timeout() -> httpx.Timeout:
    return httpx.Timeout(connect=5.0, read=30.0, write=15.0, pool=5.0)


def _validate_positive_timeout(value: httpx.Timeout | float) -> None:
    if isinstance(value, (int, float)):
        if value <= 0:
            raise AdsPowerConfigurationError("timeout must be positive")
        return
    for name in ("connect", "read", "write", "pool"):
        part = getattr(value, name)
        if part is not None and part <= 0:
            raise AdsPowerConfigurationError(f"timeout.{name} must be positive")


def _normalize_base_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"}:
        raise AdsPowerConfigurationError("base_url must use http or https")
    if not parsed.hostname:
        raise AdsPowerConfigurationError("base_url must include a host")
    if parsed.username is not None or parsed.password is not None:
        raise AdsPowerConfigurationError("base_url must not contain embedded credentials")
    if parsed.query or parsed.fragment:
        raise AdsPowerConfigurationError("base_url must not contain a query or fragment")
    if parsed.path not in {"", "/"}:
        raise AdsPowerConfigurationError("base_url must not contain a path")
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def _normalize_browser_host(value: str | None) -> str | None:
    if value is None:
        return None
    host = value.strip()
    if not host:
        return None
    if "://" in host or "/" in host or "?" in host or "#" in host:
        raise AdsPowerConfigurationError("browser_host must be a hostname or IP without scheme/path")
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    if ":" in host:
        raise AdsPowerConfigurationError("browser_host must not contain a port")
    if not _HOST_RE.fullmatch(host):
        raise AdsPowerConfigurationError("browser_host is not a valid hostname or IP address")
    return host


@dataclass(frozen=True, slots=True)
class AdsPowerConfig:
    """Resolved immutable client configuration. API keys are never shown in repr."""

    base_url: str = DEFAULT_BASE_URL
    api_key: str | None = field(default=None, repr=False)
    timeout: httpx.Timeout | float = field(default_factory=default_timeout)
    browser_start_timeout: float = 60.0
    browser_probe_timeout: float = 2.0
    browser_host: str | None = None
    browser_endpoint_policy: BrowserEndpointPolicy = "rewrite_loopback_to_api_host"

    @classmethod
    def resolve(
        cls,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: httpx.Timeout | float | None = None,
        browser_start_timeout: float | None = None,
        browser_probe_timeout: float | None = None,
        browser_host: str | None = None,
        browser_endpoint_policy: BrowserEndpointPolicy | None = None,
    ) -> "AdsPowerConfig":
        resolved_url = base_url if base_url is not None else os.getenv("ADSPOWER_BASE_URL", DEFAULT_BASE_URL)
        env_key = os.getenv("ADSPOWER_API_KEY")
        resolved_key = api_key if api_key is not None else env_key
        if resolved_key is not None:
            resolved_key = resolved_key.strip() or None
        resolved_timeout = timeout if timeout is not None else default_timeout()
        _validate_positive_timeout(resolved_timeout)
        start_timeout = browser_start_timeout if browser_start_timeout is not None else float(os.getenv("ADSPOWER_BROWSER_START_TIMEOUT", "60"))
        probe_timeout = browser_probe_timeout if browser_probe_timeout is not None else float(os.getenv("ADSPOWER_BROWSER_PROBE_TIMEOUT", "2"))
        if start_timeout <= 0 or probe_timeout <= 0:
            raise AdsPowerConfigurationError("browser timeouts must be positive")
        env_host = os.getenv("ADSPOWER_BROWSER_HOST")
        resolved_host = _normalize_browser_host(browser_host if browser_host is not None else env_host)
        policy = browser_endpoint_policy or os.getenv("ADSPOWER_BROWSER_ENDPOINT_POLICY", "rewrite_loopback_to_api_host")
        if policy not in {"rewrite_loopback_to_api_host", "exact"}:
            raise AdsPowerConfigurationError("invalid browser_endpoint_policy")
        return cls(
            base_url=_normalize_base_url(resolved_url),
            api_key=resolved_key,
            timeout=resolved_timeout,
            browser_start_timeout=start_timeout,
            browser_probe_timeout=probe_timeout,
            browser_host=resolved_host,
            browser_endpoint_policy=policy,
        )

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

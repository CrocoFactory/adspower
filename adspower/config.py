from __future__ import annotations

import os
from dataclasses import dataclass, field

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:50325"


def default_timeout() -> httpx.Timeout:
    return httpx.Timeout(connect=5.0, read=30.0, write=15.0, pool=5.0)


@dataclass(frozen=True, slots=True)
class ClientConfig:
    """Resolved, immutable client configuration."""

    base_url: str = DEFAULT_BASE_URL
    api_key: str | None = field(default=None, repr=False)
    timeout: httpx.Timeout | float = field(default_factory=default_timeout)
    browser_start_timeout: float = 60.0

    @classmethod
    def resolve(
        cls,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: httpx.Timeout | float | None = None,
        browser_start_timeout: float = 60.0,
    ) -> "ClientConfig":
        resolved_url = base_url or os.getenv("ADSPOWER_BASE_URL") or DEFAULT_BASE_URL
        resolved_key = api_key if api_key is not None else os.getenv("ADSPOWER_API_KEY")
        return cls(
            base_url=resolved_url.rstrip("/"),
            api_key=resolved_key,
            timeout=timeout if timeout is not None else default_timeout(),
            browser_start_timeout=browser_start_timeout,
        )

    @property
    def headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}"}

    def __repr__(self) -> str:
        key = "<redacted>" if self.api_key else "None"
        return (
            f"ClientConfig(base_url={self.base_url!r}, api_key={key}, "
            f"timeout={self.timeout!r}, browser_start_timeout={self.browser_start_timeout!r})"
        )

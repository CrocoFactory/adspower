from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from .config import ClientConfig
from .exceptions import (
    AdsPowerAPIError,
    AdsPowerConnectionError,
    AdsPowerTimeoutError,
    AuthenticationError,
    ProfileNotFoundError,
    RateLimitError,
)
from .rate_limit import AsyncRateLimiter, RateLimit, SyncRateLimiter


def parse_response(response: httpx.Response) -> Any:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if response.status_code in (401, 403):
            raise AuthenticationError("AdsPower rejected the API credentials") from exc
        if response.status_code == 429:
            raise RateLimitError("AdsPower rate limit exceeded") from exc
        raise AdsPowerAPIError(
            f"AdsPower returned HTTP {response.status_code}", response={"text": response.text}
        ) from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise AdsPowerAPIError("AdsPower returned invalid JSON") from exc
    if not isinstance(payload, Mapping):
        raise AdsPowerAPIError("AdsPower returned a non-object JSON response")
    code = payload.get("code")
    if code not in (0, "0", None):
        message = str(payload.get("msg") or payload.get("message") or "Unknown AdsPower API error")
        lowered = message.lower()
        error_type: type[AdsPowerAPIError] = AdsPowerAPIError
        if "auth" in lowered or "api key" in lowered or "unauthorized" in lowered:
            error_type = AuthenticationError
        elif "too many" in lowered or "rate limit" in lowered:
            error_type = RateLimitError
        elif "not found" in lowered and "profile" in lowered:
            error_type = ProfileNotFoundError
        raise error_type(message, code=code, response=dict(payload))
    return payload.get("data", payload)


class SyncTransport:
    def __init__(
        self,
        config: ClientConfig,
        *,
        rate_limit: RateLimit | None = None,
        endpoint_limits: Mapping[str, RateLimit] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config
        self._limiter = SyncRateLimiter(rate_limit) if rate_limit else None
        self._endpoint_limiters = {
            path: SyncRateLimiter(limit) for path, limit in (endpoint_limits or {}).items()
        }
        self._client = httpx.Client(
            base_url=config.base_url,
            headers=config.headers,
            timeout=config.timeout,
            transport=transport,
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
        timeout: float | httpx.Timeout | None = None,
    ) -> Any:
        limiter = self._endpoint_limiters.get(path, self._limiter)
        if limiter:
            limiter.acquire()
        try:
            kwargs: dict[str, Any] = {"params": params, "json": json}
            if timeout is not None:
                kwargs["timeout"] = timeout
            response = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise AdsPowerTimeoutError(f"AdsPower request timed out: {path}") from exc
        except (httpx.ConnectError, httpx.NetworkError, httpx.InvalidURL) as exc:
            raise AdsPowerConnectionError(f"Cannot connect to AdsPower at {self.config.base_url}") from exc
        return parse_response(response)

    def close(self) -> None:
        self._client.close()


class AsyncTransport:
    def __init__(
        self,
        config: ClientConfig,
        *,
        rate_limit: RateLimit | None = None,
        endpoint_limits: Mapping[str, RateLimit] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self._limiter = AsyncRateLimiter(rate_limit) if rate_limit else None
        self._endpoint_limiters = {
            path: AsyncRateLimiter(limit) for path, limit in (endpoint_limits or {}).items()
        }
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            headers=config.headers,
            timeout=config.timeout,
            transport=transport,
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
        timeout: float | httpx.Timeout | None = None,
    ) -> Any:
        limiter = self._endpoint_limiters.get(path, self._limiter)
        if limiter:
            await limiter.acquire()
        try:
            kwargs: dict[str, Any] = {"params": params, "json": json}
            if timeout is not None:
                kwargs["timeout"] = timeout
            response = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise AdsPowerTimeoutError(f"AdsPower request timed out: {path}") from exc
        except (httpx.ConnectError, httpx.NetworkError, httpx.InvalidURL) as exc:
            raise AdsPowerConnectionError(f"Cannot connect to AdsPower at {self.config.base_url}") from exc
        return parse_response(response)

    async def close(self) -> None:
        await self._client.aclose()

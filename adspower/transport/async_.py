from __future__ import annotations

from collections.abc import Mapping

import httpx

from .._json import JsonValue
from ..config import AdsPowerConfig
from ..errors import AdsPowerConfigurationError, AdsPowerConnectionError, AdsPowerTimeoutError
from ..rate_limit import AsyncRateLimiter, EndpointLimitKey, RateLimit


class AsyncTransport:
    """Async HTTP I/O only. Protocol decoding and domain parsing live above."""

    def __init__(
        self,
        config: AdsPowerConfig,
        *,
        rate_limit: RateLimit | None = None,
        endpoint_limits: Mapping[EndpointLimitKey, RateLimit] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self._limiter = AsyncRateLimiter(rate_limit, endpoint_limits)
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
        params: Mapping[str, str | int | float | bool | None] | None = None,
        json: JsonValue | None = None,
        timeout: float | httpx.Timeout | None = None,
    ) -> httpx.Response:
        await self._limiter.acquire(method, path)
        try:
            if timeout is None:
                return await self._client.request(method, path, params=params, json=json)
            return await self._client.request(method, path, params=params, json=json, timeout=timeout)
        except httpx.TimeoutException as exc:
            raise AdsPowerTimeoutError(
                f"AdsPower request timed out ({method.upper()} {path})",
                method=method.upper(),
                path=path,
            ) from exc
        except httpx.InvalidURL as exc:
            raise AdsPowerConfigurationError(f"Invalid AdsPower URL for {method.upper()} {path}") from exc
        except httpx.TransportError as exc:
            raise AdsPowerConnectionError(
                f"AdsPower transport failed ({method.upper()} {path})",
                method=method.upper(),
                path=path,
            ) from exc

    async def close(self) -> None:
        await self._client.aclose()

from __future__ import annotations

from collections.abc import Mapping

import httpx

from .._json import JsonValue
from ..config import AdsPowerConfig
from ..errors import AdsPowerConfigurationError, AdsPowerConnectionError, AdsPowerTimeoutError
from ..rate_limit import EndpointLimitKey, RateLimit, SyncRateLimiter


class SyncTransport:
    """HTTP I/O only. Protocol decoding and domain parsing live above this layer."""

    def __init__(
        self,
        config: AdsPowerConfig,
        *,
        rate_limit: RateLimit | None = None,
        endpoint_limits: Mapping[EndpointLimitKey, RateLimit] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config
        self._limiter = SyncRateLimiter(rate_limit, endpoint_limits)
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
        params: Mapping[str, str | int | float | bool | None] | None = None,
        json: JsonValue | None = None,
        timeout: float | httpx.Timeout | None = None,
    ) -> httpx.Response:
        self._limiter.acquire(method, path)
        try:
            kwargs: dict[str, object] = {"params": params, "json": json}
            if timeout is not None:
                kwargs["timeout"] = timeout
            return self._client.request(method, path, **kwargs)
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

    def close(self) -> None:
        self._client.close()

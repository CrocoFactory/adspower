from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

import httpx

from .config import ClientConfig
from .exceptions import (
    AdsPowerAPIError,
    AdsPowerConfigurationError,
    AdsPowerConnectionError,
    AdsPowerResponseError,
    AdsPowerTimeoutError,
    AuthenticationError,
    ProfileNotFoundError,
    RateLimitError,
)
from .rate_limit import AsyncRateLimiter, EndpointLimitKey, RateLimit, SyncRateLimiter
from .security import redact_sensitive


def _normalized_path(path: str) -> str:
    parsed = urlsplit(path)
    return parsed.path or path


def _retry_after(response: httpx.Response) -> float | None:
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


def _safe_response_payload(response: httpx.Response) -> dict[str, Any] | None:
    try:
        payload = response.json()
    except ValueError:
        return {"status_code": response.status_code}
    if isinstance(payload, Mapping):
        return {
            "status_code": response.status_code,
            "body": redact_sensitive(dict(payload)),
        }
    return {"status_code": response.status_code}


def _business_error_type(message: str) -> type[AdsPowerAPIError]:
    """Best-effort compatibility fallback when AdsPower exposes no stable error code."""
    lowered = message.lower()
    if "auth" in lowered or "api key" in lowered or "unauthorized" in lowered:
        return AuthenticationError
    if "too many" in lowered or "rate limit" in lowered:
        return RateLimitError
    if "not found" in lowered and "profile" in lowered:
        return ProfileNotFoundError
    return AdsPowerAPIError


def decode_response(
    response: httpx.Response,
    *,
    method: str,
    path: str,
    unwrap: bool,
) -> Any:
    """Decode one Local API response with identical error semantics for all callers."""
    method = method.upper()
    normalized_path = _normalized_path(path)
    status = response.status_code

    if status >= 400:
        kwargs = {
            "method": method,
            "path": normalized_path,
            "response": _safe_response_payload(response),
        }
        if status in {401, 403}:
            raise AuthenticationError(
                f"AdsPower rejected credentials ({method} {normalized_path})",
                **kwargs,
            )
        if status == 429:
            raise RateLimitError(
                f"AdsPower rate limit exceeded ({method} {normalized_path})",
                retry_after=_retry_after(response),
                **kwargs,
            )
        raise AdsPowerAPIError(
            f"AdsPower returned HTTP {status} ({method} {normalized_path})",
            **kwargs,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise AdsPowerResponseError(
            f"AdsPower returned invalid JSON ({method} {normalized_path})",
            method=method,
            path=normalized_path,
        ) from exc

    if not isinstance(payload, Mapping):
        if unwrap:
            return payload
        raise AdsPowerResponseError(
            f"AdsPower returned a non-object response envelope ({method} {normalized_path})",
            method=method,
            path=normalized_path,
        )

    code = payload.get("code")
    if code not in (0, "0", None):
        message = str(payload.get("msg") or payload.get("message") or "Unknown AdsPower API error")
        error_type = _business_error_type(message)
        kwargs = {
            "code": code,
            "response": redact_sensitive(dict(payload)),
            "method": method,
            "path": normalized_path,
        }
        if error_type is RateLimitError:
            raise RateLimitError(
                f"{message} ({method} {normalized_path})",
                retry_after=_retry_after(response),
                **kwargs,
            )
        raise error_type(f"{message} ({method} {normalized_path})", **kwargs)

    return payload.get("data", payload) if unwrap else dict(payload)


def parse_response(response: httpx.Response, *, method: str = "GET", path: str = "") -> Any:
    """Backward-compatible wrapper around the single response decoder."""
    return decode_response(response, method=method, path=path, unwrap=True)


def _parse_envelope(response: httpx.Response, *, method: str, path: str) -> dict[str, Any]:
    """Backward-compatible wrapper returning the validated full response envelope."""
    decoded = decode_response(response, method=method, path=path, unwrap=False)
    if not isinstance(decoded, dict):
        raise AdsPowerResponseError(
            f"AdsPower returned an invalid response envelope ({method.upper()} {_normalized_path(path)})",
            method=method.upper(),
            path=_normalized_path(path),
        )
    return decoded


def _normalize_endpoint_limits(
    endpoint_limits: Mapping[EndpointLimitKey, RateLimit] | None,
) -> dict[tuple[str | None, str], RateLimit]:
    normalized: dict[tuple[str | None, str], RateLimit] = {}
    for key, limit in (endpoint_limits or {}).items():
        if isinstance(key, tuple):
            if len(key) != 2:
                raise AdsPowerConfigurationError("endpoint limit tuple keys must be (method, path)")
            method, path = key
            normalized[(str(method).upper(), _normalized_path(str(path)))] = limit
        else:
            normalized[(None, _normalized_path(str(key)))] = limit
    return normalized


class SyncTransport:
    """Synchronous HTTPX transport with normalized errors and cumulative rate limits."""

    def __init__(
        self,
        config: ClientConfig,
        *,
        rate_limit: RateLimit | None = None,
        endpoint_limits: Mapping[EndpointLimitKey, RateLimit] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config
        self._limiter = SyncRateLimiter(rate_limit) if rate_limit else None
        self._endpoint_limiters = {
            key: SyncRateLimiter(limit)
            for key, limit in _normalize_endpoint_limits(endpoint_limits).items()
        }
        self._client = httpx.Client(
            base_url=config.base_url,
            headers=config.headers,
            timeout=config.timeout,
            transport=transport,
        )

    def _acquire_limits(self, method: str, path: str) -> None:
        if self._limiter is not None:
            self._limiter.acquire()
        normalized_path = _normalized_path(path)
        endpoint_limiter = self._endpoint_limiters.get(
            (method.upper(), normalized_path)
        ) or self._endpoint_limiters.get((None, normalized_path))
        if endpoint_limiter is not None:
            endpoint_limiter.acquire()

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
        self._acquire_limits(method, path)
        try:
            kwargs: dict[str, Any] = {"params": params, "json": json}
            if timeout is not None:
                kwargs["timeout"] = timeout
            response = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise AdsPowerTimeoutError(
                f"AdsPower request timed out ({method.upper()} {_normalized_path(path)})",
                method=method.upper(),
                path=_normalized_path(path),
            ) from exc
        except httpx.InvalidURL as exc:
            raise AdsPowerConfigurationError(
                f"Invalid AdsPower URL for {method.upper()} {_normalized_path(path)}"
            ) from exc
        except httpx.TransportError as exc:
            raise AdsPowerConnectionError(
                f"AdsPower transport failed ({method.upper()} {_normalized_path(path)})",
                method=method.upper(),
                path=_normalized_path(path),
            ) from exc
        return decode_response(response, method=method, path=path, unwrap=unwrap)

    def close(self) -> None:
        self._client.close()


class AsyncTransport:
    """Asynchronous HTTPX transport with normalized errors and cumulative rate limits."""

    def __init__(
        self,
        config: ClientConfig,
        *,
        rate_limit: RateLimit | None = None,
        endpoint_limits: Mapping[EndpointLimitKey, RateLimit] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self._limiter = AsyncRateLimiter(rate_limit) if rate_limit else None
        self._endpoint_limiters = {
            key: AsyncRateLimiter(limit)
            for key, limit in _normalize_endpoint_limits(endpoint_limits).items()
        }
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            headers=config.headers,
            timeout=config.timeout,
            transport=transport,
        )

    async def _acquire_limits(self, method: str, path: str) -> None:
        if self._limiter is not None:
            await self._limiter.acquire()
        normalized_path = _normalized_path(path)
        endpoint_limiter = self._endpoint_limiters.get(
            (method.upper(), normalized_path)
        ) or self._endpoint_limiters.get((None, normalized_path))
        if endpoint_limiter is not None:
            await endpoint_limiter.acquire()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        timeout: float | httpx.Timeout | None = None,
        unwrap: bool = True,
    ) -> Any:
        await self._acquire_limits(method, path)
        try:
            kwargs: dict[str, Any] = {"params": params, "json": json}
            if timeout is not None:
                kwargs["timeout"] = timeout
            response = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise AdsPowerTimeoutError(
                f"AdsPower request timed out ({method.upper()} {_normalized_path(path)})",
                method=method.upper(),
                path=_normalized_path(path),
            ) from exc
        except httpx.InvalidURL as exc:
            raise AdsPowerConfigurationError(
                f"Invalid AdsPower URL for {method.upper()} {_normalized_path(path)}"
            ) from exc
        except httpx.TransportError as exc:
            raise AdsPowerConnectionError(
                f"AdsPower transport failed ({method.upper()} {_normalized_path(path)})",
                method=method.upper(),
                path=_normalized_path(path),
            ) from exc
        return decode_response(response, method=method, path=path, unwrap=unwrap)

    async def close(self) -> None:
        await self._client.aclose()

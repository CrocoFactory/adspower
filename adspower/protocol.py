from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

import httpx

from ._json import JsonValue, require_json_value, require_object
from .errors import AdsPowerAPIError, AdsPowerAuthenticationError, AdsPowerProtocolError, AdsPowerRateLimitError

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class AdsPowerEnvelope(Generic[T]):
    code: int
    message: str
    data: T | None


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def _message(payload: dict[str, JsonValue]) -> str:
    value = payload.get("msg", payload.get("message", ""))
    if value is None:
        return ""
    if not isinstance(value, str):
        raise AdsPowerProtocolError("AdsPower response message must be a string")
    return value


def _code(value: JsonValue | None) -> int:
    if isinstance(value, bool):
        raise AdsPowerProtocolError("AdsPower response code must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            pass
    raise AdsPowerProtocolError("AdsPower response is missing a valid code")


def decode_response(
    response: httpx.Response,
    *,
    method: str,
    path: str,
    allow_plain_object: bool = False,
) -> AdsPowerEnvelope[JsonValue]:
    """Validate one Local API HTTP response without message-substring heuristics."""
    method = method.upper()
    status = response.status_code
    if status >= 400:
        kwargs = {"method": method, "path": path, "status": status}
        if status in {401, 403}:
            raise AdsPowerAuthenticationError(
                f"AdsPower rejected credentials ({method} {path})", **kwargs
            )
        if status == 429:
            raise AdsPowerRateLimitError(
                f"AdsPower rate limit exceeded ({method} {path})",
                retry_after=_retry_after(response),
                **kwargs,
            )
        raise AdsPowerAPIError(f"AdsPower returned HTTP {status} ({method} {path})", **kwargs)

    try:
        raw = response.json()
    except ValueError as exc:
        raise AdsPowerProtocolError(
            f"AdsPower returned invalid JSON ({method} {path})", method=method, path=path
        ) from exc

    payload = require_object(raw, field="response")
    if "code" not in payload and allow_plain_object:
        return AdsPowerEnvelope(code=0, message="", data=payload)

    code = _code(payload.get("code"))
    message = _message(payload)
    if code != 0:
        raise AdsPowerAPIError(
            f"{message or 'AdsPower rejected the operation'} ({method} {path})",
            method=method,
            path=path,
            status=status,
            code=code,
            server_message=message or None,
        )
    data = require_json_value(payload.get("data"), field="data") if "data" in payload else None
    return AdsPowerEnvelope(code=code, message=message, data=data)

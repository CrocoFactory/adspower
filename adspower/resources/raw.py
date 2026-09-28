from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlsplit

import httpx

from .._json import JsonValue
from ..errors import AdsPowerValidationError
from ..protocol import AdsPowerEnvelope
from ._common import AsyncTransportProtocol, SyncTransportProtocol, response_envelope


def _path(path: str) -> str:
    parsed = urlsplit(path)
    if parsed.scheme or parsed.netloc or not path.startswith("/") or path.startswith("//"):
        raise AdsPowerValidationError("raw requests require a root-relative path such as '/api/v2/...'")
    return path


class RawResource:
    def __init__(self, transport: SyncTransportProtocol) -> None:
        self._transport = transport

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int | float | bool | None] | None = None,
        json: JsonValue | None = None,
        timeout: float | httpx.Timeout | None = None,
    ) -> AdsPowerEnvelope[JsonValue]:
        safe_path = _path(path)
        response = self._transport.request(method, safe_path, params=params, json=json, timeout=timeout)
        return response_envelope(response, method, safe_path)


class AsyncRawResource:
    def __init__(self, transport: AsyncTransportProtocol) -> None:
        self._transport = transport

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int | float | bool | None] | None = None,
        json: JsonValue | None = None,
        timeout: float | httpx.Timeout | None = None,
    ) -> AdsPowerEnvelope[JsonValue]:
        safe_path = _path(path)
        response = await self._transport.request(method, safe_path, params=params, json=json, timeout=timeout)
        return response_envelope(response, method, safe_path)

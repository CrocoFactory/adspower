from __future__ import annotations

from typing import Literal

from .. import _contracts as c
from .._json import JsonValue
from ._common import AsyncTransportProtocol, SyncTransportProtocol, response_data


class AppResource:
    def __init__(self, transport: SyncTransportProtocol) -> None:
        self._transport = transport

    def update_patch(self, version_type: Literal["stable", "beta"] = "stable") -> JsonValue | None:
        return response_data(self._transport.request(c.APP_UPDATE_PATCH.method, c.APP_UPDATE_PATCH.path, json={"version_type": version_type}), c.APP_UPDATE_PATCH)


class AsyncAppResource:
    def __init__(self, transport: AsyncTransportProtocol) -> None:
        self._transport = transport

    async def update_patch(self, version_type: Literal["stable", "beta"] = "stable") -> JsonValue | None:
        return response_data(await self._transport.request(c.APP_UPDATE_PATCH.method, c.APP_UPDATE_PATCH.path, json={"version_type": version_type}), c.APP_UPDATE_PATCH)

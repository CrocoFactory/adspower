from __future__ import annotations

from .. import _contracts as c
from .._json import JsonObject, require_object
from ._common import AsyncTransportProtocol, SyncTransportProtocol, response_data


class HealthResource:
    def __init__(self, transport: SyncTransportProtocol) -> None:
        self._transport = transport

    def status(self) -> JsonObject:
        data = response_data(self._transport.request(c.STATUS.method, c.STATUS.path), c.STATUS, allow_plain_object=True)
        return require_object(data, field="status")


class AsyncHealthResource:
    def __init__(self, transport: AsyncTransportProtocol) -> None:
        self._transport = transport

    async def status(self) -> JsonObject:
        data = response_data(
            await self._transport.request(c.STATUS.method, c.STATUS.path), c.STATUS, allow_plain_object=True
        )
        return require_object(data, field="status")

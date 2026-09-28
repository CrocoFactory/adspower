from __future__ import annotations

from .. import _contracts as c
from .._json import JsonObject, require_object
from ..protocol import decode_response
from ._common import AsyncTransportProtocol, SyncTransportProtocol


class HealthResource:
    def __init__(self, transport: SyncTransportProtocol) -> None:
        self._transport = transport

    def status(self) -> JsonObject:
        envelope = decode_response(
            self._transport.request(c.STATUS.method, c.STATUS.path),
            method=c.STATUS.method,
            path=c.STATUS.path,
            allow_plain_object=True,
        )
        if envelope.data is None:
            return {"code": envelope.code, "message": envelope.message}
        return require_object(envelope.data, field="status")


class AsyncHealthResource:
    def __init__(self, transport: AsyncTransportProtocol) -> None:
        self._transport = transport

    async def status(self) -> JsonObject:
        envelope = decode_response(
            await self._transport.request(c.STATUS.method, c.STATUS.path),
            method=c.STATUS.method,
            path=c.STATUS.path,
            allow_plain_object=True,
        )
        if envelope.data is None:
            return {"code": envelope.code, "message": envelope.message}
        return require_object(envelope.data, field="status")

from __future__ import annotations

from typing import Literal

from .. import _contracts as c
from .._json import JsonValue, require_list, require_object
from ..models import KernelInfo
from ..models.kernels import parse_kernel
from ._common import AsyncTransportProtocol, SyncTransportProtocol, response_data


def _kernels(value: object) -> tuple[KernelInfo, ...]:
    if isinstance(value, list):
        items = value
    else:
        data = require_object(value, field="kernels")
        raw = data.get("list", data.get("items", data.get("kernels")))
        items = require_list(raw, field="kernels")
    return tuple(parse_kernel(item) for item in items)


class KernelsResource:
    def __init__(self, transport: SyncTransportProtocol) -> None:
        self._transport = transport

    def list(self, *, kernel_type: Literal["Chrome", "Firefox"] | None = None) -> tuple[KernelInfo, ...]:
        data = response_data(
            self._transport.request(c.KERNEL_LIST.method, c.KERNEL_LIST.path, params={"kernel_type": kernel_type}),
            c.KERNEL_LIST,
        )
        return _kernels(data)

    def download(self, kernel_type: Literal["Chrome", "Firefox"], kernel_version: str) -> JsonValue | None:
        return response_data(
            self._transport.request(
                c.KERNEL_DOWNLOAD.method,
                c.KERNEL_DOWNLOAD.path,
                json={"kernel_type": kernel_type, "kernel_version": kernel_version},
            ),
            c.KERNEL_DOWNLOAD,
        )


class AsyncKernelsResource:
    def __init__(self, transport: AsyncTransportProtocol) -> None:
        self._transport = transport

    async def list(self, *, kernel_type: Literal["Chrome", "Firefox"] | None = None) -> tuple[KernelInfo, ...]:
        data = response_data(
            await self._transport.request(
                c.KERNEL_LIST.method, c.KERNEL_LIST.path, params={"kernel_type": kernel_type}
            ),
            c.KERNEL_LIST,
        )
        return _kernels(data)

    async def download(self, kernel_type: Literal["Chrome", "Firefox"], kernel_version: str) -> JsonValue | None:
        return response_data(
            await self._transport.request(
                c.KERNEL_DOWNLOAD.method,
                c.KERNEL_DOWNLOAD.path,
                json={"kernel_type": kernel_type, "kernel_version": kernel_version},
            ),
            c.KERNEL_DOWNLOAD,
        )

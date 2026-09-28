from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Literal

from typing_extensions import TypedDict, Unpack

from .. import _contracts as c
from .._json import JsonValue, first_present, require_object
from ..errors import AdsPowerProtocolError
from ..models import Page, Proxy
from ..models.proxies import StoredProxyConfig, parse_proxy
from ._common import (
    AsyncTransportProtocol,
    SyncTransportProtocol,
    compact,
    id_list,
    parse_page,
    response_data,
    validate_page,
)


class ProxyUpdateOptions(TypedDict, total=False):
    proxy_type: Literal["http", "https", "ssh", "socks5"]
    host: str
    port: int | str
    user: str
    password: str
    proxy_url: str
    remark: str
    ipchecker: Literal["ip2location", "ipapi", "ipfoxy"]


def _proxy_update(profile_id: str, fields: dict[str, object]) -> dict[str, JsonValue]:
    body: dict[str, JsonValue] = {"proxy_id": profile_id}
    for key, value in fields.items():
        if value is None:
            continue
        wire_key = "type" if key == "proxy_type" else key
        body[wire_key] = str(value) if key == "port" else value  # type: ignore[assignment]
    return body


def _created_proxy_ids(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        raw = value
    else:
        data = require_object(value, field="proxy create")
        candidate = first_present(data, "proxy_id", "proxy_ids", "id")
        raw = candidate if isinstance(candidate, list) else [candidate]
    result: list[str] = []
    for item in raw:
        if item in (None, "") or isinstance(item, bool) or not isinstance(item, (str, int)):
            raise AdsPowerProtocolError("proxy create response contains an invalid proxy id")
        result.append(str(item))
    if not result:
        raise AdsPowerProtocolError("proxy create response does not contain ids")
    return tuple(result)


class ProxiesResource:
    def __init__(self, transport: SyncTransportProtocol) -> None:
        self._transport = transport

    def create(self, config: StoredProxyConfig) -> tuple[str, ...]:
        return self.create_many([config])

    def create_many(self, configs: Sequence[StoredProxyConfig]) -> tuple[str, ...]:
        if isinstance(configs, (str, bytes)) or not configs:
            from ..errors import AdsPowerValidationError

            raise AdsPowerValidationError("configs must be a non-empty sequence")
        data = response_data(
            self._transport.request(
                c.PROXY_CREATE.method, c.PROXY_CREATE.path, json=[config.to_api() for config in configs]
            ),
            c.PROXY_CREATE,
        )
        return _created_proxy_ids(data)

    def update(self, proxy_id: str, **options: Unpack[ProxyUpdateOptions]) -> None:
        response_data(
            self._transport.request(
                c.PROXY_UPDATE.method, c.PROXY_UPDATE.path, json=_proxy_update(proxy_id, dict(options))
            ),
            c.PROXY_UPDATE,
        )

    def list(self, *, proxy_ids: Sequence[str] | None = None, page: int = 1, page_size: int = 50) -> Page[Proxy]:
        validate_page(page, page_size, maximum=200)
        body = compact(
            {
                "proxy_id": [str(item) for item in proxy_ids] if proxy_ids is not None else None,
                "page": page,
                "limit": page_size,
            }
        )
        data = response_data(self._transport.request(c.PROXY_LIST.method, c.PROXY_LIST.path, json=body), c.PROXY_LIST)
        return parse_page(
            data, item_keys=("list", "items"), parser=parse_proxy, requested_page=page, requested_page_size=page_size
        )

    def iter_all(
        self, *, proxy_ids: Sequence[str] | None = None, page: int = 1, page_size: int = 50
    ) -> Iterator[Proxy]:
        """Iterate proxies across all pages."""
        while True:
            current = self.list(proxy_ids=proxy_ids, page=page, page_size=page_size)
            yield from current.items
            if current.total_pages is not None:
                if page >= current.total_pages:
                    break
            elif len(current.items) < page_size:
                break
            page += 1

    def delete(self, proxy_id: str) -> None:
        self.delete_many([proxy_id])

    def delete_many(self, proxy_ids: Sequence[str]) -> None:
        response_data(
            self._transport.request(
                c.PROXY_DELETE.method,
                c.PROXY_DELETE.path,
                json={"proxy_id": id_list(proxy_ids, name="proxy_ids", maximum=100)},
            ),
            c.PROXY_DELETE,
        )


class AsyncProxiesResource:
    def __init__(self, transport: AsyncTransportProtocol) -> None:
        self._transport = transport

    async def create(self, config: StoredProxyConfig) -> tuple[str, ...]:
        return await self.create_many([config])

    async def create_many(self, configs: Sequence[StoredProxyConfig]) -> tuple[str, ...]:
        if isinstance(configs, (str, bytes)) or not configs:
            from ..errors import AdsPowerValidationError

            raise AdsPowerValidationError("configs must be a non-empty sequence")
        data = response_data(
            await self._transport.request(
                c.PROXY_CREATE.method, c.PROXY_CREATE.path, json=[config.to_api() for config in configs]
            ),
            c.PROXY_CREATE,
        )
        return _created_proxy_ids(data)

    async def update(self, proxy_id: str, **options: Unpack[ProxyUpdateOptions]) -> None:
        response_data(
            await self._transport.request(
                c.PROXY_UPDATE.method, c.PROXY_UPDATE.path, json=_proxy_update(proxy_id, dict(options))
            ),
            c.PROXY_UPDATE,
        )

    async def list(self, *, proxy_ids: Sequence[str] | None = None, page: int = 1, page_size: int = 50) -> Page[Proxy]:
        validate_page(page, page_size, maximum=200)
        body = compact(
            {
                "proxy_id": [str(item) for item in proxy_ids] if proxy_ids is not None else None,
                "page": page,
                "limit": page_size,
            }
        )
        data = response_data(
            await self._transport.request(c.PROXY_LIST.method, c.PROXY_LIST.path, json=body), c.PROXY_LIST
        )
        return parse_page(
            data, item_keys=("list", "items"), parser=parse_proxy, requested_page=page, requested_page_size=page_size
        )

    async def iter_all(
        self, *, proxy_ids: Sequence[str] | None = None, page: int = 1, page_size: int = 50
    ) -> AsyncIterator[Proxy]:
        """Iterate proxies across all pages."""
        while True:
            current = await self.list(proxy_ids=proxy_ids, page=page, page_size=page_size)
            for item in current.items:
                yield item
            if current.total_pages is not None:
                if page >= current.total_pages:
                    break
            elif len(current.items) < page_size:
                break
            page += 1

    async def delete(self, proxy_id: str) -> None:
        await self.delete_many([proxy_id])

    async def delete_many(self, proxy_ids: Sequence[str]) -> None:
        response_data(
            await self._transport.request(
                c.PROXY_DELETE.method,
                c.PROXY_DELETE.path,
                json={"proxy_id": id_list(proxy_ids, name="proxy_ids", maximum=100)},
            ),
            c.PROXY_DELETE,
        )

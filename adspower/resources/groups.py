from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

from .. import _contracts as c
from ..models import Group, Page
from ..models.profiles import parse_group
from ._common import AsyncTransportProtocol, SyncTransportProtocol, compact, parse_page, response_data, validate_page


class GroupsResource:
    def __init__(self, transport: SyncTransportProtocol) -> None:
        self._transport = transport

    def create(self, name: str, *, remark: str | None = None) -> Group:
        data = response_data(
            self._transport.request(
                c.GROUP_CREATE.method, c.GROUP_CREATE.path, json=compact({"group_name": name, "remark": remark})
            ),
            c.GROUP_CREATE,
        )
        return parse_group(data)

    def update(self, group_id: str, *, name: str, remark: str | None = None) -> None:
        response_data(
            self._transport.request(
                c.GROUP_UPDATE.method,
                c.GROUP_UPDATE.path,
                json=compact({"group_id": group_id, "group_name": name, "remark": remark}),
            ),
            c.GROUP_UPDATE,
        )

    def list(self, *, name: str | None = None, page: int = 1, page_size: int = 10) -> Page[Group]:
        validate_page(page, page_size, maximum=100)
        params = {"page": page, "page_size": page_size, "group_name": name}
        data = response_data(
            self._transport.request(c.GROUP_LIST.method, c.GROUP_LIST.path, params=params), c.GROUP_LIST
        )
        return parse_page(
            data, item_keys=("list", "items"), parser=parse_group, requested_page=page, requested_page_size=page_size
        )

    def iter_all(self, *, name: str | None = None, page: int = 1, page_size: int = 10) -> Iterator[Group]:
        """Iterate groups across all pages."""
        while True:
            current = self.list(name=name, page=page, page_size=page_size)
            yield from current.items
            if current.total_pages is not None:
                if page >= current.total_pages:
                    break
            elif len(current.items) < page_size:
                break
            page += 1


class AsyncGroupsResource:
    def __init__(self, transport: AsyncTransportProtocol) -> None:
        self._transport = transport

    async def create(self, name: str, *, remark: str | None = None) -> Group:
        data = response_data(
            await self._transport.request(
                c.GROUP_CREATE.method, c.GROUP_CREATE.path, json=compact({"group_name": name, "remark": remark})
            ),
            c.GROUP_CREATE,
        )
        return parse_group(data)

    async def update(self, group_id: str, *, name: str, remark: str | None = None) -> None:
        response_data(
            await self._transport.request(
                c.GROUP_UPDATE.method,
                c.GROUP_UPDATE.path,
                json=compact({"group_id": group_id, "group_name": name, "remark": remark}),
            ),
            c.GROUP_UPDATE,
        )

    async def list(self, *, name: str | None = None, page: int = 1, page_size: int = 10) -> Page[Group]:
        validate_page(page, page_size, maximum=100)
        params = {"page": page, "page_size": page_size, "group_name": name}
        data = response_data(
            await self._transport.request(c.GROUP_LIST.method, c.GROUP_LIST.path, params=params), c.GROUP_LIST
        )
        return parse_page(
            data, item_keys=("list", "items"), parser=parse_group, requested_page=page, requested_page_size=page_size
        )

    async def iter_all(self, *, name: str | None = None, page: int = 1, page_size: int = 10) -> AsyncIterator[Group]:
        """Iterate groups across all pages."""
        while True:
            current = await self.list(name=name, page=page, page_size=page_size)
            for item in current.items:
                yield item
            if current.total_pages is not None:
                if page >= current.total_pages:
                    break
            elif len(current.items) < page_size:
                break
            page += 1

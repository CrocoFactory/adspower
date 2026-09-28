from __future__ import annotations

from .. import _contracts as c
from ..models import Category, Page
from ..models.profiles import parse_category
from ._common import AsyncTransportProtocol, SyncTransportProtocol, parse_page, response_data, validate_page


class CategoriesResource:
    def __init__(self, transport: SyncTransportProtocol) -> None:
        self._transport = transport

    def list(self, *, category_id: str | None = None, page: int = 1, page_size: int = 200) -> Page[Category]:
        validate_page(page, page_size, maximum=200)
        params = {"category_id": category_id, "page": page, "limit": page_size}
        data = response_data(self._transport.request(c.CATEGORY_LIST.method, c.CATEGORY_LIST.path, params=params), c.CATEGORY_LIST)
        return parse_page(data, item_keys=("list", "items"), parser=parse_category, requested_page=page, requested_page_size=page_size)


class AsyncCategoriesResource:
    def __init__(self, transport: AsyncTransportProtocol) -> None:
        self._transport = transport

    async def list(self, *, category_id: str | None = None, page: int = 1, page_size: int = 200) -> Page[Category]:
        validate_page(page, page_size, maximum=200)
        params = {"category_id": category_id, "page": page, "limit": page_size}
        data = response_data(await self._transport.request(c.CATEGORY_LIST.method, c.CATEGORY_LIST.path, params=params), c.CATEGORY_LIST)
        return parse_page(data, item_keys=("list", "items"), parser=parse_category, requested_page=page, requested_page_size=page_size)

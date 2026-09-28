from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from .. import _contracts as c
from .._json import JsonObject, JsonValue
from ..errors import AdsPowerValidationError
from ..models import BrowserTag, Page
from ..models.tags import parse_browser_tag
from ._common import AsyncTransportProtocol, SyncTransportProtocol, id_list, parse_page, response_data, validate_page

TagColor = Literal["darkBlue", "blue", "purple", "red", "yellow", "orange", "green", "lightGreen"]


@dataclass(frozen=True, slots=True)
class TagCreate:
    name: str
    color: TagColor | None = None

    def to_api(self) -> JsonObject:
        if not self.name or len(self.name) > 50:
            raise AdsPowerValidationError("tag name must contain 1 to 50 characters")
        value: JsonObject = {"name": self.name}
        if self.color is not None:
            value["color"] = self.color
        return value


@dataclass(frozen=True, slots=True)
class TagUpdate:
    tag_id: str
    name: str | None = None
    color: TagColor | None = None

    def to_api(self) -> JsonObject:
        if self.name is not None and (not self.name or len(self.name) > 50):
            raise AdsPowerValidationError("tag name must contain 1 to 50 characters")
        value: JsonObject = {"id": self.tag_id}
        if self.name is not None:
            value["name"] = self.name
        if self.color is not None:
            value["color"] = self.color
        return value


class TagsResource:
    def __init__(self, transport: SyncTransportProtocol) -> None:
        self._transport = transport

    def list(self, *, ids: Sequence[str] | None = None, page: int = 1, page_size: int = 50) -> Page[BrowserTag]:
        validate_page(page, page_size, maximum=200)
        if ids is not None and len(ids) > 100:
            raise AdsPowerValidationError("ids must contain at most 100 tag ids")
        body: JsonObject = {"page": page, "limit": page_size}
        if ids is not None:
            body["ids"] = [str(item) for item in ids]
        data = response_data(self._transport.request(c.TAG_LIST.method, c.TAG_LIST.path, json=body), c.TAG_LIST)
        return parse_page(data, item_keys=("list", "items", "tags"), parser=parse_browser_tag, requested_page=page, requested_page_size=page_size)

    def create(self, tags: Sequence[TagCreate]) -> JsonValue | None:
        if not tags:
            raise AdsPowerValidationError("tags must not be empty")
        return response_data(self._transport.request(c.TAG_CREATE.method, c.TAG_CREATE.path, json={"tags": [tag.to_api() for tag in tags]}), c.TAG_CREATE)

    def update(self, tags: Sequence[TagUpdate]) -> None:
        if not tags:
            raise AdsPowerValidationError("tags must not be empty")
        response_data(self._transport.request(c.TAG_UPDATE.method, c.TAG_UPDATE.path, json={"tags": [tag.to_api() for tag in tags]}), c.TAG_UPDATE)

    def delete(self, ids: Sequence[str]) -> None:
        response_data(self._transport.request(c.TAG_DELETE.method, c.TAG_DELETE.path, json={"ids": id_list(ids, name="ids")}), c.TAG_DELETE)


class AsyncTagsResource:
    def __init__(self, transport: AsyncTransportProtocol) -> None:
        self._transport = transport

    async def list(self, *, ids: Sequence[str] | None = None, page: int = 1, page_size: int = 50) -> Page[BrowserTag]:
        validate_page(page, page_size, maximum=200)
        if ids is not None and len(ids) > 100:
            raise AdsPowerValidationError("ids must contain at most 100 tag ids")
        body: JsonObject = {"page": page, "limit": page_size}
        if ids is not None:
            body["ids"] = [str(item) for item in ids]
        data = response_data(await self._transport.request(c.TAG_LIST.method, c.TAG_LIST.path, json=body), c.TAG_LIST)
        return parse_page(data, item_keys=("list", "items", "tags"), parser=parse_browser_tag, requested_page=page, requested_page_size=page_size)

    async def create(self, tags: Sequence[TagCreate]) -> JsonValue | None:
        if not tags:
            raise AdsPowerValidationError("tags must not be empty")
        return response_data(await self._transport.request(c.TAG_CREATE.method, c.TAG_CREATE.path, json={"tags": [tag.to_api() for tag in tags]}), c.TAG_CREATE)

    async def update(self, tags: Sequence[TagUpdate]) -> None:
        if not tags:
            raise AdsPowerValidationError("tags must not be empty")
        response_data(await self._transport.request(c.TAG_UPDATE.method, c.TAG_UPDATE.path, json={"tags": [tag.to_api() for tag in tags]}), c.TAG_UPDATE)

    async def delete(self, ids: Sequence[str]) -> None:
        response_data(await self._transport.request(c.TAG_DELETE.method, c.TAG_DELETE.path, json={"ids": id_list(ids, name="ids")}), c.TAG_DELETE)

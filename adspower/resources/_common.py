from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator, Mapping, Sequence
from typing import Protocol, TypeVar

import httpx

from .._contracts import Endpoint
from .._json import JsonObject, JsonValue, optional_int, require_list, require_object
from ..errors import AdsPowerProtocolError, AdsPowerValidationError
from ..models.common import Page
from ..protocol import AdsPowerEnvelope, decode_response

T = TypeVar("T")
Params = Mapping[str, str | int | float | bool | None]


class SyncTransportProtocol(Protocol):
    def request(
        self,
        method: str,
        path: str,
        *,
        params: Params | None = None,
        json: JsonValue | None = None,
        timeout: float | httpx.Timeout | None = None,
    ) -> httpx.Response: ...


class AsyncTransportProtocol(Protocol):
    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Params | None = None,
        json: JsonValue | None = None,
        timeout: float | httpx.Timeout | None = None,
    ) -> httpx.Response: ...


def compact(values: Mapping[str, JsonValue | None]) -> JsonObject:
    return {key: value for key, value in values.items() if value is not None}


def selector(profile_id: str | None, profile_no: str | None) -> JsonObject:
    if bool(profile_id) == bool(profile_no):
        raise AdsPowerValidationError("exactly one of profile_id or profile_no is required")
    return {"profile_id": profile_id} if profile_id else {"profile_no": profile_no}


def id_list(
    values: Sequence[str],
    *,
    name: str,
    maximum: int | None = None,
) -> list[JsonValue]:
    if isinstance(values, (str, bytes)):
        raise AdsPowerValidationError(f"{name} must be a sequence, not a string")
    result = [str(value) for value in values if str(value)]
    if not result or len(result) != len(values):
        raise AdsPowerValidationError(f"{name} must contain non-empty ids")
    if maximum is not None and len(result) > maximum:
        raise AdsPowerValidationError(f"{name} must contain at most {maximum} ids")
    return result


def bool_wire(value: bool) -> str:
    return "1" if value else "0"


def response_data(
    response: httpx.Response,
    endpoint: Endpoint,
    *,
    allow_plain_object: bool = False,
) -> JsonValue | None:
    return decode_response(
        response,
        method=endpoint.method,
        path=endpoint.path,
        allow_plain_object=allow_plain_object,
    ).data


def response_envelope(response: httpx.Response, method: str, path: str) -> AdsPowerEnvelope[JsonValue]:
    return decode_response(response, method=method, path=path)


def parse_page(
    data: object,
    *,
    item_keys: tuple[str, ...],
    parser: Callable[[object], T],
    requested_page: int,
    requested_page_size: int,
) -> Page[T]:
    if isinstance(data, list):
        raw_items: object = data
        meta: JsonObject = {}
    else:
        meta = require_object(data, field="page")
        raw_items = None
        for key in item_keys:
            if key in meta:
                raw_items = meta[key]
                break
        if raw_items is None:
            raise AdsPowerProtocolError(
                f"paginated response is missing one of: {', '.join(item_keys)}"
            )
    items = require_list(raw_items, field="page items")
    page = optional_int(meta.get("page"), field="page") if meta else None
    page_size = optional_int(meta.get("page_size", meta.get("limit")), field="page_size") if meta else None
    total_count = optional_int(meta.get("total_count"), field="total_count") if meta else None
    total_pages = optional_int(meta.get("total_pages"), field="total_pages") if meta else None
    if page is not None and page < 1:
        raise AdsPowerProtocolError("response page must be >= 1")
    if page_size is not None and page_size < 1:
        raise AdsPowerProtocolError("response page_size must be >= 1")
    if total_count is not None and total_count < 0:
        raise AdsPowerProtocolError("response total_count must be >= 0")
    if total_pages is not None and total_pages < 0:
        raise AdsPowerProtocolError("response total_pages must be >= 0")
    return Page(
        tuple(parser(item) for item in items),
        page or requested_page,
        page_size or requested_page_size,
        total_count,
        total_pages,
    )


def validate_page(page: int, page_size: int, *, maximum: int) -> None:
    if page < 1:
        raise AdsPowerValidationError("page must be >= 1")
    if not 1 <= page_size <= maximum:
        raise AdsPowerValidationError(f"page_size must be between 1 and {maximum}")

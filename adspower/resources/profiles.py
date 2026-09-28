from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Literal

from typing_extensions import TypedDict, Unpack

from .. import _contracts as c
from .._json import JsonObject, JsonValue, require_json_value, require_list, require_object
from ..errors import AdsPowerNotFoundError, AdsPowerProtocolError, AdsPowerValidationError
from ..models import CreatedProfile, FingerprintConfig, InlineProxyConfig, Page, PlatformAccount, Profile
from ..models.profiles import parse_created_profile, parse_profile
from ._common import (
    AsyncTransportProtocol,
    SyncTransportProtocol,
    bool_wire,
    compact,
    id_list,
    parse_page,
    response_data,
    selector,
    validate_page,
)

NameFilter = Literal["include", "exclude"]
SortType = Literal["profile_no", "last_open_time", "created_time"]
SortOrder = Literal["asc", "desc"]
CacheType = Literal["local_storage", "indexeddb", "extension_cache", "cookie", "history", "image_file"]
IpChecker = Literal["ip2location", "ipapi", "ipfoxy"]
TagsUpdateMode = Literal["replace", "append"]


class ProfileCreateOptions(TypedDict, total=False):
    username: str
    password: str
    cookie: str
    fakey: str
    platform: str
    remark: str
    tabs: Sequence[str]
    user_proxy_config: InlineProxyConfig
    proxyid: str
    repeat_config: Literal[0, 2, 3, 4]
    ignore_cookie_error: bool
    ip: str
    country: str
    region: str
    city: str
    ipchecker: IpChecker
    category_id: str
    profile_tag_ids: Sequence[str]
    platform_account: PlatformAccount
    fingerprint_config: FingerprintConfig


class ProfileUpdateOptions(TypedDict, total=False):
    group_id: str
    username: str
    password: str
    cookie: str
    fakey: str
    name: str
    platform: str
    remark: str
    tabs: Sequence[str]
    user_proxy_config: InlineProxyConfig
    proxyid: str
    ignore_cookie_error: bool
    ip: str
    country: str
    region: str
    city: str
    ipchecker: IpChecker
    category_id: str
    profile_tag_ids: Sequence[str]
    platform_account: PlatformAccount
    fingerprint_config: FingerprintConfig
    launch_args: str | Sequence[str]
    tags_update_type: TagsUpdateMode


def _profile_fields(fields: dict[str, object], *, create: bool) -> JsonObject:
    result: JsonObject = {}
    for key, value in fields.items():
        if value is None:
            continue
        if key == "user_proxy_config":
            if not isinstance(value, InlineProxyConfig):
                raise AdsPowerValidationError("user_proxy_config must be InlineProxyConfig")
            result[key] = value.to_api()
        elif key == "fingerprint_config":
            if not isinstance(value, FingerprintConfig):
                raise AdsPowerValidationError("fingerprint_config must be FingerprintConfig")
            result[key] = value.to_api()
        elif key == "platform_account":
            if not isinstance(value, PlatformAccount):
                raise AdsPowerValidationError("platform_account must be PlatformAccount")
            result[key] = value.to_api()
        elif key in {"ignore_cookie_error"}:
            if not isinstance(value, bool):
                raise AdsPowerValidationError(f"{key} must be bool")
            result[key] = bool_wire(value)
        elif key == "repeat_config":
            if value not in {0, 2, 3, 4}:
                raise AdsPowerValidationError("repeat_config must be one of 0, 2, 3, 4")
            result[key] = str(value)
        elif key == "tags_update_type":
            if value not in {"replace", "append"}:
                raise AdsPowerValidationError("tags_update_type must be replace or append")
            result[key] = "1" if value == "replace" else "2"
        elif key == "tabs":
            if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
                raise AdsPowerValidationError("tabs must be a sequence of strings")
            if any(not isinstance(item, str) for item in value):
                raise AdsPowerValidationError("tabs must contain only strings")
            result[key] = list(value)
        elif key == "profile_tag_ids":
            if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
                raise AdsPowerValidationError("profile_tag_ids must be a sequence of strings")
            if len(value) > 30:
                raise AdsPowerValidationError("profile_tag_ids must contain at most 30 tag ids")
            if any(not isinstance(item, str) for item in value):
                raise AdsPowerValidationError("profile_tag_ids must contain only strings")
            result[key] = list(value)
        elif key == "launch_args":
            if isinstance(value, str):
                result[key] = value
            elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                if any(not isinstance(item, str) for item in value):
                    raise AdsPowerValidationError("launch_args must contain only strings")
                result[key] = list(value)
            else:
                raise AdsPowerValidationError("launch_args must be a string or sequence of strings")
        elif key in {
            "group_id",
            "username",
            "password",
            "cookie",
            "fakey",
            "name",
            "platform",
            "remark",
            "proxyid",
            "ip",
            "country",
            "region",
            "city",
            "ipchecker",
            "category_id",
        }:
            if not isinstance(value, str):
                raise AdsPowerValidationError(f"{key} must be a string")
            if key == "ipchecker" and value not in {"ip2location", "ipapi", "ipfoxy"}:
                raise AdsPowerValidationError("ipchecker must be ip2location, ipapi, or ipfoxy")
            result[key] = value
        else:
            raise AdsPowerValidationError(f"unsupported profile field: {key}")
    if create and "proxyid" not in result and "user_proxy_config" not in result:
        result["user_proxy_config"] = InlineProxyConfig.no_proxy().to_api()
    _validate_profile_payload(result)
    return result


def _validate_profile_payload(payload: JsonObject) -> None:
    group_id = payload.get("group_id")
    if group_id is not None and (not isinstance(group_id, str) or not group_id.isdigit()):
        raise AdsPowerValidationError("group_id must be a numeric string")
    name = payload.get("name")
    if isinstance(name, str) and len(name) > 100:
        raise AdsPowerValidationError("name must contain at most 100 characters")
    remark = payload.get("remark")
    if isinstance(remark, str) and len(remark) > 1500:
        raise AdsPowerValidationError("remark must contain at most 1500 characters")
    country = payload.get("country")
    if country is not None and (
        not isinstance(country, str) or len(country) != 2 or not country.isalpha() or country.lower() != country
    ):
        raise AdsPowerValidationError("country must be a lowercase two-letter code")


def _profile_list_body(
    *,
    group_id: str | None,
    profile_id: Sequence[str] | str | None,
    profile_no: Sequence[str] | str | None,
    sort_type: SortType | None,
    sort_order: SortOrder | None,
    tag_ids: Sequence[str] | None,
    tags_filter: NameFilter | None,
    name: str | None,
    name_filter: NameFilter | None,
    page: int,
    page_size: int,
) -> JsonObject:
    if (
        isinstance(page, bool)
        or not isinstance(page, int)
        or isinstance(page_size, bool)
        or not isinstance(page_size, int)
    ):
        raise AdsPowerValidationError("page and page_size must be integers")
    validate_page(page, page_size, maximum=200)
    if group_id is not None and not isinstance(group_id, str):
        raise AdsPowerValidationError("group_id must be a string")
    if sort_type is not None and sort_type not in {"profile_no", "last_open_time", "created_time"}:
        raise AdsPowerValidationError("invalid sort_type")
    if sort_order is not None and sort_order not in {"asc", "desc"}:
        raise AdsPowerValidationError("invalid sort_order")
    if tags_filter is not None and tags_filter not in {"include", "exclude"}:
        raise AdsPowerValidationError("tags_filter must be include or exclude")
    if name_filter is not None and name_filter not in {"include", "exclude"}:
        raise AdsPowerValidationError("name_filter must be include or exclude")
    if name is not None and not isinstance(name, str):
        raise AdsPowerValidationError("name must be a string")

    def many(value: Sequence[str] | str | None, *, field: str) -> JsonValue | None:
        if value is None:
            return None
        if isinstance(value, str):
            return [value]
        if isinstance(value, (bytes, bytearray)) or not isinstance(value, Sequence):
            raise AdsPowerValidationError(f"{field} must be a string or sequence of strings")
        if any(not isinstance(item, str) for item in value):
            raise AdsPowerValidationError(f"{field} must contain only strings")
        return list(value)

    tag_values: JsonValue | None = None
    if tag_ids is not None:
        if isinstance(tag_ids, (str, bytes)) or not isinstance(tag_ids, Sequence):
            raise AdsPowerValidationError("tag_ids must be a sequence of strings")
        if any(not isinstance(item, str) for item in tag_ids):
            raise AdsPowerValidationError("tag_ids must contain only strings")
        tag_values = list(tag_ids)

    return compact(
        {
            "group_id": group_id,
            "profile_id": many(profile_id, field="profile_id"),
            "profile_no": many(profile_no, field="profile_no"),
            "sort_type": sort_type,
            "sort_order": sort_order,
            "tag_ids": tag_values,
            "tags_filter": tags_filter,
            "name": name,
            "name_filter": name_filter,
            "page": page,
            "limit": page_size,
        }
    )


def _cookies(value: object) -> tuple[JsonObject, ...]:
    data = require_object(value, field="cookies")
    raw = data.get("cookies", data.get("cookie"))
    if isinstance(raw, str):
        import json

        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AdsPowerProtocolError("cookie response contains invalid JSON") from exc
    values = require_list(raw, field="cookies")
    return tuple(require_object(item, field="cookie") for item in values)


def _user_agents(value: object) -> JsonValue:
    if value is None:
        raise AdsPowerProtocolError("user-agent response is missing data")
    return require_json_value(value, field="user-agent")


class ProfilesResource:
    def __init__(self, transport: SyncTransportProtocol) -> None:
        self._transport = transport

    def create(
        self,
        *,
        group_id: str = "0",
        name: str | None = None,
        **options: Unpack[ProfileCreateOptions],
    ) -> CreatedProfile:
        if not isinstance(group_id, str):
            raise AdsPowerValidationError("group_id must be a numeric string")
        body = _profile_fields(dict(options), create=True)
        body.update(compact({"group_id": group_id, "name": name}))
        _validate_profile_payload(body)
        data = response_data(
            self._transport.request(c.PROFILE_CREATE.method, c.PROFILE_CREATE.path, json=body), c.PROFILE_CREATE
        )
        return parse_created_profile(data)

    def update(self, profile_id: str, **options: Unpack[ProfileUpdateOptions]) -> None:
        body = _profile_fields(dict(options), create=False)
        body["profile_id"] = profile_id
        response_data(
            self._transport.request(c.PROFILE_UPDATE.method, c.PROFILE_UPDATE.path, json=body), c.PROFILE_UPDATE
        )

    def list(
        self,
        *,
        group_id: str | None = None,
        profile_id: Sequence[str] | str | None = None,
        profile_no: Sequence[str] | str | None = None,
        sort_type: SortType | None = None,
        sort_order: SortOrder | None = None,
        tag_ids: Sequence[str] | None = None,
        tags_filter: NameFilter | None = None,
        name: str | None = None,
        name_filter: NameFilter | None = None,
        page: int = 1,
        page_size: int = 200,
    ) -> Page[Profile]:
        """Return one server-side filtered profile page."""
        body = _profile_list_body(
            group_id=group_id,
            profile_id=profile_id,
            profile_no=profile_no,
            sort_type=sort_type,
            sort_order=sort_order,
            tag_ids=tag_ids,
            tags_filter=tags_filter,
            name=name,
            name_filter=name_filter,
            page=page,
            page_size=page_size,
        )
        data = response_data(
            self._transport.request(c.PROFILE_LIST.method, c.PROFILE_LIST.path, json=body), c.PROFILE_LIST
        )
        return parse_page(
            data,
            item_keys=("list", "profiles", "items"),
            parser=parse_profile,
            requested_page=page,
            requested_page_size=page_size,
        )

    def iter_all(
        self,
        *,
        group_id: str | None = None,
        profile_id: Sequence[str] | str | None = None,
        profile_no: Sequence[str] | str | None = None,
        sort_type: SortType | None = None,
        sort_order: SortOrder | None = None,
        tag_ids: Sequence[str] | None = None,
        tags_filter: NameFilter | None = None,
        name: str | None = None,
        name_filter: NameFilter | None = None,
        page: int = 1,
        page_size: int = 200,
    ) -> Iterator[Profile]:
        """Iterate matching profiles across all returned pages."""
        while True:
            current = self.list(
                group_id=group_id,
                profile_id=profile_id,
                profile_no=profile_no,
                sort_type=sort_type,
                sort_order=sort_order,
                tag_ids=tag_ids,
                tags_filter=tags_filter,
                name=name,
                name_filter=name_filter,
                page=page,
                page_size=page_size,
            )
            yield from current.items
            if current.total_pages is not None:
                if page >= current.total_pages:
                    break
            elif len(current.items) < page_size:
                break
            page += 1

    def get(self, profile_id: str) -> Profile:
        page = self.list(profile_id=profile_id, page_size=1)
        if not page.items:
            raise AdsPowerNotFoundError(f"profile {profile_id!r} was not found")
        return page.items[0]

    def find_by_name(self, name: str, *, group_id: str | None = None) -> Profile | None:
        page = self.list(name=name, name_filter="include", group_id=group_id)
        return next((profile for profile in page.items if profile.name == name), None)

    def delete(self, profile_id: str) -> None:
        self.delete_many([profile_id])

    def delete_many(self, profile_ids: Sequence[str]) -> None:
        response_data(
            self._transport.request(
                c.PROFILE_DELETE.method,
                c.PROFILE_DELETE.path,
                json={"profile_id": id_list(profile_ids, name="profile_ids")},
            ),
            c.PROFILE_DELETE,
        )

    def move(self, profile_ids: Sequence[str], group_id: str) -> None:
        if not isinstance(group_id, str) or not group_id.isdigit():
            raise AdsPowerValidationError("group_id must be a numeric string")
        response_data(
            self._transport.request(
                c.PROFILE_MOVE.method,
                c.PROFILE_MOVE.path,
                json={"user_ids": id_list(profile_ids, name="profile_ids"), "group_id": group_id},
            ),
            c.PROFILE_MOVE,
        )

    def cookies(self, *, profile_id: str | None = None, profile_no: str | None = None) -> tuple[JsonObject, ...]:
        payload = selector(profile_id, profile_no)
        params = {key: str(value) for key, value in payload.items()}
        data = response_data(
            self._transport.request(c.PROFILE_COOKIES.method, c.PROFILE_COOKIES.path, params=params), c.PROFILE_COOKIES
        )
        return _cookies(data)

    def user_agents(
        self,
        *,
        profile_ids: Sequence[str] | None = None,
        profile_nos: Sequence[str] | None = None,
    ) -> JsonValue:
        if bool(profile_ids) == bool(profile_nos):
            raise AdsPowerValidationError("provide exactly one of profile_ids or profile_nos")
        values = profile_ids if profile_ids is not None else profile_nos
        assert values is not None
        body: JsonObject = {
            "profile_id" if profile_ids is not None else "profile_no": id_list(values, name="profiles", maximum=10)
        }
        data = response_data(self._transport.request(c.PROFILE_UA.method, c.PROFILE_UA.path, json=body), c.PROFILE_UA)
        return _user_agents(data)

    def new_fingerprint(
        self,
        *,
        profile_ids: Sequence[str] | None = None,
        profile_nos: Sequence[str] | None = None,
    ) -> JsonValue | None:
        if bool(profile_ids) == bool(profile_nos):
            raise AdsPowerValidationError("provide exactly one of profile_ids or profile_nos")
        values = profile_ids if profile_ids is not None else profile_nos
        assert values is not None
        body: JsonObject = {
            "profile_id" if profile_ids is not None else "profile_no": id_list(values, name="profiles", maximum=10)
        }
        return response_data(
            self._transport.request(c.PROFILE_NEW_FINGERPRINT.method, c.PROFILE_NEW_FINGERPRINT.path, json=body),
            c.PROFILE_NEW_FINGERPRINT,
        )

    def delete_cache(self, profile_ids: Sequence[str], cache_types: Sequence[CacheType]) -> None:
        if isinstance(cache_types, (str, bytes)) or not cache_types:
            raise AdsPowerValidationError("cache_types must be a non-empty sequence")
        response_data(
            self._transport.request(
                c.PROFILE_DELETE_CACHE.method,
                c.PROFILE_DELETE_CACHE.path,
                json={"profile_id": id_list(profile_ids, name="profile_ids"), "type": list(cache_types)},
            ),
            c.PROFILE_DELETE_CACHE,
        )

    def share(
        self,
        profile_ids: Sequence[str],
        receiver: str,
        *,
        share_type: Literal["email", "phone"] = "email",
        content: Sequence[Literal["name", "proxy", "remark", "tabs"]] | None = None,
    ) -> JsonValue | None:
        body = compact(
            {
                "profile_id": id_list(profile_ids, name="profile_ids", maximum=200),
                "receiver": receiver,
                "share_type": 1 if share_type == "email" else 2,
                "content": list(content) if content is not None else None,
            }
        )
        return response_data(
            self._transport.request(c.PROFILE_SHARE.method, c.PROFILE_SHARE.path, json=body), c.PROFILE_SHARE
        )


class AsyncProfilesResource:
    def __init__(self, transport: AsyncTransportProtocol) -> None:
        self._transport = transport

    async def create(
        self, *, group_id: str = "0", name: str | None = None, **options: Unpack[ProfileCreateOptions]
    ) -> CreatedProfile:
        if not isinstance(group_id, str):
            raise AdsPowerValidationError("group_id must be a numeric string")
        body = _profile_fields(dict(options), create=True)
        body.update(compact({"group_id": group_id, "name": name}))
        _validate_profile_payload(body)
        data = response_data(
            await self._transport.request(c.PROFILE_CREATE.method, c.PROFILE_CREATE.path, json=body), c.PROFILE_CREATE
        )
        return parse_created_profile(data)

    async def update(self, profile_id: str, **options: Unpack[ProfileUpdateOptions]) -> None:
        body = _profile_fields(dict(options), create=False)
        body["profile_id"] = profile_id
        response_data(
            await self._transport.request(c.PROFILE_UPDATE.method, c.PROFILE_UPDATE.path, json=body), c.PROFILE_UPDATE
        )

    async def list(
        self,
        *,
        group_id: str | None = None,
        profile_id: Sequence[str] | str | None = None,
        profile_no: Sequence[str] | str | None = None,
        sort_type: SortType | None = None,
        sort_order: SortOrder | None = None,
        tag_ids: Sequence[str] | None = None,
        tags_filter: NameFilter | None = None,
        name: str | None = None,
        name_filter: NameFilter | None = None,
        page: int = 1,
        page_size: int = 200,
    ) -> Page[Profile]:
        """Return one server-side filtered profile page."""
        body = _profile_list_body(
            group_id=group_id,
            profile_id=profile_id,
            profile_no=profile_no,
            sort_type=sort_type,
            sort_order=sort_order,
            tag_ids=tag_ids,
            tags_filter=tags_filter,
            name=name,
            name_filter=name_filter,
            page=page,
            page_size=page_size,
        )
        data = response_data(
            await self._transport.request(c.PROFILE_LIST.method, c.PROFILE_LIST.path, json=body), c.PROFILE_LIST
        )
        return parse_page(
            data,
            item_keys=("list", "profiles", "items"),
            parser=parse_profile,
            requested_page=page,
            requested_page_size=page_size,
        )

    async def iter_all(
        self,
        *,
        group_id: str | None = None,
        profile_id: Sequence[str] | str | None = None,
        profile_no: Sequence[str] | str | None = None,
        sort_type: SortType | None = None,
        sort_order: SortOrder | None = None,
        tag_ids: Sequence[str] | None = None,
        tags_filter: NameFilter | None = None,
        name: str | None = None,
        name_filter: NameFilter | None = None,
        page: int = 1,
        page_size: int = 200,
    ) -> AsyncIterator[Profile]:
        """Iterate matching profiles across all returned pages."""
        while True:
            current = await self.list(
                group_id=group_id,
                profile_id=profile_id,
                profile_no=profile_no,
                sort_type=sort_type,
                sort_order=sort_order,
                tag_ids=tag_ids,
                tags_filter=tags_filter,
                name=name,
                name_filter=name_filter,
                page=page,
                page_size=page_size,
            )
            for item in current.items:
                yield item
            if current.total_pages is not None:
                if page >= current.total_pages:
                    break
            elif len(current.items) < page_size:
                break
            page += 1

    async def get(self, profile_id: str) -> Profile:
        page = await self.list(profile_id=profile_id, page_size=1)
        if not page.items:
            raise AdsPowerNotFoundError(f"profile {profile_id!r} was not found")
        return page.items[0]

    async def find_by_name(self, name: str, *, group_id: str | None = None) -> Profile | None:
        page = await self.list(name=name, name_filter="include", group_id=group_id)
        return next((profile for profile in page.items if profile.name == name), None)

    async def delete(self, profile_id: str) -> None:
        await self.delete_many([profile_id])

    async def delete_many(self, profile_ids: Sequence[str]) -> None:
        response_data(
            await self._transport.request(
                c.PROFILE_DELETE.method,
                c.PROFILE_DELETE.path,
                json={"profile_id": id_list(profile_ids, name="profile_ids")},
            ),
            c.PROFILE_DELETE,
        )

    async def move(self, profile_ids: Sequence[str], group_id: str) -> None:
        if not isinstance(group_id, str) or not group_id.isdigit():
            raise AdsPowerValidationError("group_id must be a numeric string")
        response_data(
            await self._transport.request(
                c.PROFILE_MOVE.method,
                c.PROFILE_MOVE.path,
                json={"user_ids": id_list(profile_ids, name="profile_ids"), "group_id": group_id},
            ),
            c.PROFILE_MOVE,
        )

    async def cookies(self, *, profile_id: str | None = None, profile_no: str | None = None) -> tuple[JsonObject, ...]:
        payload = selector(profile_id, profile_no)
        params = {key: str(value) for key, value in payload.items()}
        data = response_data(
            await self._transport.request(c.PROFILE_COOKIES.method, c.PROFILE_COOKIES.path, params=params),
            c.PROFILE_COOKIES,
        )
        return _cookies(data)

    async def user_agents(
        self, *, profile_ids: Sequence[str] | None = None, profile_nos: Sequence[str] | None = None
    ) -> JsonValue:
        if bool(profile_ids) == bool(profile_nos):
            raise AdsPowerValidationError("provide exactly one of profile_ids or profile_nos")
        values = profile_ids if profile_ids is not None else profile_nos
        assert values is not None
        body: JsonObject = {
            "profile_id" if profile_ids is not None else "profile_no": id_list(values, name="profiles", maximum=10)
        }
        data = response_data(
            await self._transport.request(c.PROFILE_UA.method, c.PROFILE_UA.path, json=body), c.PROFILE_UA
        )
        return _user_agents(data)

    async def new_fingerprint(
        self, *, profile_ids: Sequence[str] | None = None, profile_nos: Sequence[str] | None = None
    ) -> JsonValue | None:
        if bool(profile_ids) == bool(profile_nos):
            raise AdsPowerValidationError("provide exactly one of profile_ids or profile_nos")
        values = profile_ids if profile_ids is not None else profile_nos
        assert values is not None
        body: JsonObject = {
            "profile_id" if profile_ids is not None else "profile_no": id_list(values, name="profiles", maximum=10)
        }
        return response_data(
            await self._transport.request(c.PROFILE_NEW_FINGERPRINT.method, c.PROFILE_NEW_FINGERPRINT.path, json=body),
            c.PROFILE_NEW_FINGERPRINT,
        )

    async def delete_cache(self, profile_ids: Sequence[str], cache_types: Sequence[CacheType]) -> None:
        if isinstance(cache_types, (str, bytes)) or not cache_types:
            raise AdsPowerValidationError("cache_types must be a non-empty sequence")
        response_data(
            await self._transport.request(
                c.PROFILE_DELETE_CACHE.method,
                c.PROFILE_DELETE_CACHE.path,
                json={"profile_id": id_list(profile_ids, name="profile_ids"), "type": list(cache_types)},
            ),
            c.PROFILE_DELETE_CACHE,
        )

    async def share(
        self,
        profile_ids: Sequence[str],
        receiver: str,
        *,
        share_type: Literal["email", "phone"] = "email",
        content: Sequence[Literal["name", "proxy", "remark", "tabs"]] | None = None,
    ) -> JsonValue | None:
        body = compact(
            {
                "profile_id": id_list(profile_ids, name="profile_ids", maximum=200),
                "receiver": receiver,
                "share_type": 1 if share_type == "email" else 2,
                "content": list(content) if content is not None else None,
            }
        )
        return response_data(
            await self._transport.request(c.PROFILE_SHARE.method, c.PROFILE_SHARE.path, json=body), c.PROFILE_SHARE
        )

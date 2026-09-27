from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from .exceptions import AdsPowerAPIError, AdsPowerValidationError, ProfileNotFoundError
from .models import BrowserConnection, BrowserStatus, Category, Group, Profile, ProfileSelector, Proxy, RunningBrowser
from .types import CacheType


def _compact(data: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


def _items(data: Any) -> list[Mapping[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, Mapping)]
    if isinstance(data, Mapping):
        for key in ("list", "profiles", "items", "proxy_list", "category_list", "active"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, Mapping)]
    return []


def _v2_list_payload(page: int, page_size: int, filters: Mapping[str, Any]) -> tuple[dict[str, Any], str | None]:
    request_filters = dict(filters)
    name = request_filters.pop("name", None)
    for key in ("profile_id", "profile_no"):
        if key in request_filters and isinstance(request_filters[key], str):
            request_filters[key] = [request_filters[key]]
    return _compact({"page": page, "limit": page_size, **request_filters}), name


def _ids(values: Sequence[str], *, name: str, maximum: int) -> list[str]:
    result = [str(value) for value in values]
    if not 1 <= len(result) <= maximum:
        raise AdsPowerValidationError(f"{name} must contain between 1 and {maximum} items")
    return result


def _selector(profile_id: str | None = None, profile_no: str | None = None) -> ProfileSelector:
    try:
        return ProfileSelector(profile_id=profile_id, profile_no=profile_no)
    except ValueError as exc:
        raise AdsPowerValidationError(str(exc)) from exc


def _cookies(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, Mapping):
        raise AdsPowerAPIError("AdsPower returned an invalid cookies response")
    value = data.get("cookies", data.get("cookie", data))
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise AdsPowerAPIError("AdsPower returned invalid cookie JSON") from exc
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise AdsPowerAPIError("AdsPower returned cookies in an unsupported format")
    return [dict(item) for item in value]


def _profile_default_fields(fields: dict[str, Any]) -> None:
    if fields.get("proxyid") is None and fields.get("user_proxy_config") is None:
        fields["user_proxy_config"] = {"proxy_soft": "no_proxy"}
    if fields.get("fingerprint_config") is None:
        fields["fingerprint_config"] = {"automatic_timezone": "1", "language": ["en-US", "en"], "flash": "block", "webrtc": "disabled"}


class ProfilesAPI:
    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def create(self, *, name: str | None = None, group_id: str = "0", **fields: Any) -> Profile:
        _profile_default_fields(fields)
        data = self._transport.request("POST", "/api/v2/browser-profile/create", json=_compact({"name": name, "group_id": group_id, **fields}))
        return Profile.from_api(data)

    def update(self, profile_id: str, *, refresh: bool = False, **fields: Any) -> Profile | None:
        data = self._transport.request("POST", "/api/v2/browser-profile/update", json=_compact({"profile_id": profile_id, **fields}))
        if isinstance(data, Mapping) and any(key in data for key in ("profile_id", "user_id", "id")):
            return Profile.from_api(data)
        return self.get(profile_id) if refresh else None

    def list(self, *, page: int = 1, page_size: int = 100, **filters: Any) -> list[Profile]:
        if not 1 <= page_size <= 100:
            raise AdsPowerValidationError("profile page_size must be between 1 and 100")
        payload, name = _v2_list_payload(page, page_size, filters)
        data = self._transport.request("POST", "/api/v2/browser-profile/list", json=payload)
        profiles = [Profile.from_api(item) for item in _items(data)]
        return profiles if name is None else [profile for profile in profiles if profile.name == name]

    def find_by_name(self, name: str, *, page_size: int = 100, max_pages: int | None = None) -> Profile | None:
        matches = self.find_all_by_name(name, page_size=page_size, max_pages=max_pages)
        return matches[0] if matches else None

    def find_all_by_name(self, name: str, *, page_size: int = 100, max_pages: int | None = None) -> list[Profile]:
        page, matches = 1, []
        while max_pages is None or page <= max_pages:
            profiles = self.list(page=page, page_size=page_size)
            matches.extend(profile for profile in profiles if profile.name == name)
            if len(profiles) < page_size:
                break
            page += 1
        return matches

    def get(self, profile_id: str) -> Profile:
        profiles = self.list(profile_id=profile_id, page_size=1)
        if not profiles:
            raise ProfileNotFoundError(f"Profile {profile_id!r} was not found")
        return profiles[0]

    def delete(self, profile_id: str) -> None:
        self.delete_many([profile_id])

    def delete_many(self, profile_ids: Sequence[str]) -> None:
        self._transport.request("POST", "/api/v2/browser-profile/delete", json={"profile_id": _ids(profile_ids, name="profile_ids", maximum=100)})

    def move(self, profile_ids: Sequence[str], group_id: str) -> None:
        self._transport.request("POST", "/api/v1/user/regroup", json={"user_ids": _ids(profile_ids, name="profile_ids", maximum=100), "group_id": str(group_id)})

    def delete_cache(self, profile_ids: Sequence[str], cache_types: Sequence[CacheType | str]) -> None:
        self._transport.request("POST", "/api/v2/browser-profile/delete-cache", json={"profile_id": _ids(profile_ids, name="profile_ids", maximum=100), "type": [str(item) for item in cache_types]})

    def cookies(self, *, profile_id: str | None = None, profile_no: str | None = None) -> list[dict[str, Any]]:
        data = self._transport.request("GET", "/api/v2/browser-profile/cookies", params=_selector(profile_id, profile_no).payload)
        return _cookies(data)

    def share(self, profile_ids: Sequence[str], receiver: str, *, content: Sequence[str] | None = None, share_type: int = 1) -> dict[str, Any]:
        data = self._transport.request("POST", "/api/v2/browser-profile/share", json=_compact({"profile_id": _ids(profile_ids, name="profile_ids", maximum=200), "receiver": receiver, "content": list(content) if content is not None else None, "share_type": share_type}))
        return dict(data) if isinstance(data, Mapping) else {"data": data}


class AsyncProfilesAPI:
    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def create(self, *, name: str | None = None, group_id: str = "0", **fields: Any) -> Profile:
        _profile_default_fields(fields)
        data = await self._transport.request("POST", "/api/v2/browser-profile/create", json=_compact({"name": name, "group_id": group_id, **fields}))
        return Profile.from_api(data)

    async def update(self, profile_id: str, *, refresh: bool = False, **fields: Any) -> Profile | None:
        data = await self._transport.request("POST", "/api/v2/browser-profile/update", json=_compact({"profile_id": profile_id, **fields}))
        if isinstance(data, Mapping) and any(key in data for key in ("profile_id", "user_id", "id")):
            return Profile.from_api(data)
        return await self.get(profile_id) if refresh else None

    async def list(self, *, page: int = 1, page_size: int = 100, **filters: Any) -> list[Profile]:
        if not 1 <= page_size <= 100:
            raise AdsPowerValidationError("profile page_size must be between 1 and 100")
        payload, name = _v2_list_payload(page, page_size, filters)
        data = await self._transport.request("POST", "/api/v2/browser-profile/list", json=payload)
        profiles = [Profile.from_api(item) for item in _items(data)]
        return profiles if name is None else [profile for profile in profiles if profile.name == name]

    async def find_by_name(self, name: str, *, page_size: int = 100, max_pages: int | None = None) -> Profile | None:
        matches = await self.find_all_by_name(name, page_size=page_size, max_pages=max_pages)
        return matches[0] if matches else None

    async def find_all_by_name(self, name: str, *, page_size: int = 100, max_pages: int | None = None) -> list[Profile]:
        page, matches = 1, []
        while max_pages is None or page <= max_pages:
            profiles = await self.list(page=page, page_size=page_size)
            matches.extend(profile for profile in profiles if profile.name == name)
            if len(profiles) < page_size:
                break
            page += 1
        return matches

    async def get(self, profile_id: str) -> Profile:
        profiles = await self.list(profile_id=profile_id, page_size=1)
        if not profiles:
            raise ProfileNotFoundError(f"Profile {profile_id!r} was not found")
        return profiles[0]

    async def delete(self, profile_id: str) -> None:
        await self.delete_many([profile_id])

    async def delete_many(self, profile_ids: Sequence[str]) -> None:
        await self._transport.request("POST", "/api/v2/browser-profile/delete", json={"profile_id": _ids(profile_ids, name="profile_ids", maximum=100)})

    async def move(self, profile_ids: Sequence[str], group_id: str) -> None:
        await self._transport.request("POST", "/api/v1/user/regroup", json={"user_ids": _ids(profile_ids, name="profile_ids", maximum=100), "group_id": str(group_id)})

    async def delete_cache(self, profile_ids: Sequence[str], cache_types: Sequence[CacheType | str]) -> None:
        await self._transport.request("POST", "/api/v2/browser-profile/delete-cache", json={"profile_id": _ids(profile_ids, name="profile_ids", maximum=100), "type": [str(item) for item in cache_types]})

    async def cookies(self, *, profile_id: str | None = None, profile_no: str | None = None) -> list[dict[str, Any]]:
        data = await self._transport.request("GET", "/api/v2/browser-profile/cookies", params=_selector(profile_id, profile_no).payload)
        return _cookies(data)

    async def share(self, profile_ids: Sequence[str], receiver: str, *, content: Sequence[str] | None = None, share_type: int = 1) -> dict[str, Any]:
        data = await self._transport.request("POST", "/api/v2/browser-profile/share", json=_compact({"profile_id": _ids(profile_ids, name="profile_ids", maximum=200), "receiver": receiver, "content": list(content) if content is not None else None, "share_type": share_type}))
        return dict(data) if isinstance(data, Mapping) else {"data": data}


class GroupsAPI:
    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def create(self, name: str, remark: str | None = None) -> Group:
        return Group.from_api(self._transport.request("POST", "/api/v1/group/create", json=_compact({"group_name": name, "remark": remark})))

    def list(self, *, name: str | None = None, page: int = 1, page_size: int = 100) -> list[Group]:
        if not 1 <= page_size <= 2000:
            raise AdsPowerValidationError("group page_size must be between 1 and 2000")
        data = self._transport.request("GET", "/api/v1/group/list", params=_compact({"group_name": name, "page": page, "page_size": page_size}))
        return [Group.from_api(item) for item in _items(data)]

    def update(self, group_id: str, *, name: str, remark: str | None = None) -> Group:
        self._transport.request("POST", "/api/v1/group/update", json=_compact({"group_id": group_id, "group_name": name, "remark": remark}))
        return Group(id=group_id, name=name, remark=remark)


class AsyncGroupsAPI:
    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def create(self, name: str, remark: str | None = None) -> Group:
        return Group.from_api(await self._transport.request("POST", "/api/v1/group/create", json=_compact({"group_name": name, "remark": remark})))

    async def list(self, *, name: str | None = None, page: int = 1, page_size: int = 100) -> list[Group]:
        if not 1 <= page_size <= 2000:
            raise AdsPowerValidationError("group page_size must be between 1 and 2000")
        data = await self._transport.request("GET", "/api/v1/group/list", params=_compact({"group_name": name, "page": page, "page_size": page_size}))
        return [Group.from_api(item) for item in _items(data)]

    async def update(self, group_id: str, *, name: str, remark: str | None = None) -> Group:
        await self._transport.request("POST", "/api/v1/group/update", json=_compact({"group_id": group_id, "group_name": name, "remark": remark}))
        return Group(id=group_id, name=name, remark=remark)


class ProxiesAPI:
    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def create(self, *, type: str, host: str, port: str | int, user: str | None = None, password: str | None = None, **fields: Any) -> list[str]:
        data = self._transport.request("POST", "/api/v2/proxy-list/create", json=_compact({"proxy_type": type, "proxy_host": host, "proxy_port": str(port), "proxy_user": user, "proxy_password": password, **fields}))
        ids = data.get("proxy_id", data.get("proxy_ids", data.get("id", []))) if isinstance(data, Mapping) else data
        return [str(item) for item in (ids if isinstance(ids, list) else [ids]) if item is not None]

    def update(self, proxy_id: str, **fields: Any) -> None:
        self._transport.request("POST", "/api/v2/proxy-list/update", json={"proxy_id": str(proxy_id), **fields})

    def delete(self, proxy_id: str) -> None:
        self.delete_many([proxy_id])

    def delete_many(self, proxy_ids: Sequence[str]) -> None:
        self._transport.request("POST", "/api/v2/proxy-list/delete", json={"proxy_id": _ids(proxy_ids, name="proxy_ids", maximum=100)})

    def list(self, *, proxy_ids: Sequence[str] | str | None = None, page: int = 1, page_size: int = 50, **filters: Any) -> list[Proxy]:
        if not 1 <= page_size <= 200:
            raise AdsPowerValidationError("proxy page_size must be between 1 and 200")
        if isinstance(proxy_ids, str):
            proxy_ids = [proxy_ids]
        if proxy_ids is not None:
            filters["proxy_id"] = _ids(proxy_ids, name="proxy_ids", maximum=100)
        data = self._transport.request("POST", "/api/v2/proxy-list/list", json={"page": page, "limit": page_size, **filters})
        return [Proxy.from_api(item) for item in _items(data)]


class AsyncProxiesAPI:
    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def create(self, *, type: str, host: str, port: str | int, user: str | None = None, password: str | None = None, **fields: Any) -> list[str]:
        data = await self._transport.request("POST", "/api/v2/proxy-list/create", json=_compact({"proxy_type": type, "proxy_host": host, "proxy_port": str(port), "proxy_user": user, "proxy_password": password, **fields}))
        ids = data.get("proxy_id", data.get("proxy_ids", data.get("id", []))) if isinstance(data, Mapping) else data
        return [str(item) for item in (ids if isinstance(ids, list) else [ids]) if item is not None]

    async def update(self, proxy_id: str, **fields: Any) -> None:
        await self._transport.request("POST", "/api/v2/proxy-list/update", json={"proxy_id": str(proxy_id), **fields})

    async def delete(self, proxy_id: str) -> None:
        await self.delete_many([proxy_id])

    async def delete_many(self, proxy_ids: Sequence[str]) -> None:
        await self._transport.request("POST", "/api/v2/proxy-list/delete", json={"proxy_id": _ids(proxy_ids, name="proxy_ids", maximum=100)})

    async def list(self, *, proxy_ids: Sequence[str] | str | None = None, page: int = 1, page_size: int = 50, **filters: Any) -> list[Proxy]:
        if not 1 <= page_size <= 200:
            raise AdsPowerValidationError("proxy page_size must be between 1 and 200")
        if isinstance(proxy_ids, str):
            proxy_ids = [proxy_ids]
        if proxy_ids is not None:
            filters["proxy_id"] = _ids(proxy_ids, name="proxy_ids", maximum=100)
        data = await self._transport.request("POST", "/api/v2/proxy-list/list", json={"page": page, "limit": page_size, **filters})
        return [Proxy.from_api(item) for item in _items(data)]


class CategoriesAPI:
    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def list(self, *, category_id: str | None = None, page: int = 1, page_size: int = 100) -> list[Category]:
        if not 1 <= page_size <= 100:
            raise AdsPowerValidationError("category page_size must be between 1 and 100")
        data = self._transport.request("GET", "/api/v2/category/list", params=_compact({"category_id": category_id, "page": page, "limit": page_size}))
        return [Category.from_api(item) for item in _items(data)]


class AsyncCategoriesAPI:
    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def list(self, *, category_id: str | None = None, page: int = 1, page_size: int = 100) -> list[Category]:
        if not 1 <= page_size <= 100:
            raise AdsPowerValidationError("category page_size must be between 1 and 100")
        data = await self._transport.request("GET", "/api/v2/category/list", params=_compact({"category_id": category_id, "page": page, "limit": page_size}))
        return [Category.from_api(item) for item in _items(data)]


class HealthAPI:
    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def check(self) -> Any:
        return self._transport.request("GET", "/status")


class AsyncHealthAPI:
    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def check(self) -> Any:
        return await self._transport.request("GET", "/status")


def parse_browser_connection(data: Any, base_url: str) -> BrowserConnection:
    if not isinstance(data, Mapping):
        raise ValueError("Browser start response data must be an object")
    return BrowserConnection.from_api(data, base_url=base_url)


def parse_browser_status(data: Any, base_url: str) -> BrowserStatus:
    if not isinstance(data, Mapping):
        raise ValueError("Browser status response data must be an object")
    status = str(data.get("status", data.get("state", "inactive")))
    connection = BrowserConnection.from_api(data, base_url=base_url) if any(key in data for key in ("ws", "debug_port", "webdriver", "selenium", "marionette_port")) else None
    known = {"status", "state", "ws", "debug_port", "webdriver", "selenium", "marionette_port"}
    return BrowserStatus(status=status, connection=connection, extra={key: value for key, value in data.items() if key not in known})


def parse_running_browsers(data: Any, base_url: str) -> list[RunningBrowser]:
    result: list[RunningBrowser] = []
    for item in _items(data):
        profile_id = item.get("profile_id", item.get("user_id"))
        if profile_id is not None:
            result.append(RunningBrowser(profile_id=str(profile_id), connection=BrowserConnection.from_api(item, base_url=base_url), extra=dict(item)))
    return result

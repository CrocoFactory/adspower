from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .exceptions import ProfileNotFoundError
from .models import BrowserConnection, Group, Profile


def _compact(data: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


def _items(data: Any) -> list[Mapping[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, Mapping)]
    if isinstance(data, Mapping):
        for key in ("list", "profiles", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, Mapping)]
    return []


class ProfilesAPI:
    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def create(self, *, name: str | None = None, group_id: str = "0", **fields: Any) -> Profile:
        payload = _compact({"name": name, "group_id": group_id, **fields})
        data = self._transport.request("POST", "/api/v2/browser-profile/create", json=payload)
        return Profile.from_api(data)

    def update(self, profile_id: str, **fields: Any) -> Profile:
        payload = _compact({"profile_id": profile_id, **fields})
        data = self._transport.request("POST", "/api/v2/browser-profile/update", json=payload)
        if isinstance(data, Mapping) and any(key in data for key in ("profile_id", "user_id", "id")):
            return Profile.from_api(data)
        return Profile(id=profile_id, extra=dict(data) if isinstance(data, Mapping) else {})

    def list(self, *, page: int = 1, page_size: int = 100, **filters: Any) -> list[Profile]:
        payload = _compact({"page": page, "page_size": page_size, **filters})
        data = self._transport.request("POST", "/api/v2/browser-profile/list", json=payload)
        return [Profile.from_api(item) for item in _items(data)]

    def get(self, profile_id: str) -> Profile:
        profiles = self.list(profile_id=profile_id, page_size=1)
        if not profiles:
            raise ProfileNotFoundError(f"Profile {profile_id!r} was not found")
        return profiles[0]

    def delete(self, profile_id: str) -> None:
        self._transport.request("POST", "/api/v2/browser-profile/delete", json={"profile_id": profile_id})


class AsyncProfilesAPI:
    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def create(self, *, name: str | None = None, group_id: str = "0", **fields: Any) -> Profile:
        payload = _compact({"name": name, "group_id": group_id, **fields})
        data = await self._transport.request("POST", "/api/v2/browser-profile/create", json=payload)
        return Profile.from_api(data)

    async def update(self, profile_id: str, **fields: Any) -> Profile:
        payload = _compact({"profile_id": profile_id, **fields})
        data = await self._transport.request("POST", "/api/v2/browser-profile/update", json=payload)
        if isinstance(data, Mapping) and any(key in data for key in ("profile_id", "user_id", "id")):
            return Profile.from_api(data)
        return Profile(id=profile_id, extra=dict(data) if isinstance(data, Mapping) else {})

    async def list(self, *, page: int = 1, page_size: int = 100, **filters: Any) -> list[Profile]:
        payload = _compact({"page": page, "page_size": page_size, **filters})
        data = await self._transport.request("POST", "/api/v2/browser-profile/list", json=payload)
        return [Profile.from_api(item) for item in _items(data)]

    async def get(self, profile_id: str) -> Profile:
        profiles = await self.list(profile_id=profile_id, page_size=1)
        if not profiles:
            raise ProfileNotFoundError(f"Profile {profile_id!r} was not found")
        return profiles[0]

    async def delete(self, profile_id: str) -> None:
        await self._transport.request("POST", "/api/v2/browser-profile/delete", json={"profile_id": profile_id})


class GroupsAPI:
    """Group operations remain on AdsPower V1 because V2 has no equivalent contract."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def create(self, name: str, remark: str | None = None) -> Group:
        data = self._transport.request("POST", "/api/v1/group/create", json=_compact({"group_name": name, "remark": remark}))
        return Group.from_api(data)

    def list(self, *, name: str | None = None, page_size: int = 100) -> list[Group]:
        data = self._transport.request("GET", "/api/v1/group/list", params=_compact({"group_name": name, "page_size": page_size}))
        return [Group.from_api(item) for item in _items(data)]

    def update(self, group_id: str, *, name: str, remark: str | None = None) -> Group:
        payload = _compact({"group_id": group_id, "group_name": name, "remark": remark})
        self._transport.request("POST", "/api/v1/group/update", json=payload)
        return Group(id=group_id, name=name, remark=remark)


class AsyncGroupsAPI:
    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def create(self, name: str, remark: str | None = None) -> Group:
        data = await self._transport.request("POST", "/api/v1/group/create", json=_compact({"group_name": name, "remark": remark}))
        return Group.from_api(data)

    async def list(self, *, name: str | None = None, page_size: int = 100) -> list[Group]:
        data = await self._transport.request("GET", "/api/v1/group/list", params=_compact({"group_name": name, "page_size": page_size}))
        return [Group.from_api(item) for item in _items(data)]

    async def update(self, group_id: str, *, name: str, remark: str | None = None) -> Group:
        payload = _compact({"group_id": group_id, "group_name": name, "remark": remark})
        await self._transport.request("POST", "/api/v1/group/update", json=payload)
        return Group(id=group_id, name=name, remark=remark)


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

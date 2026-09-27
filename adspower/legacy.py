from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .api import _compact, _items
from .models import Profile


class LegacyProfilesAPI:
    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def create(self, *, group_id: str = "0", **fields: Any) -> Profile:
        payload = _compact({"group_id": group_id, **fields})
        data = self._transport.request("POST", "/api/v1/user/create", json=payload)
        profile_id = data.get("id") if isinstance(data, Mapping) else None
        return Profile.from_api({"user_id": profile_id, **(dict(data) if isinstance(data, Mapping) else {})})

    def list(self, **filters: Any) -> list[Profile]:
        data = self._transport.request("GET", "/api/v1/user/list", params=_compact(filters))
        return [Profile.from_api(item) for item in _items(data)]

    def delete(self, profile_id: str) -> None:
        self._transport.request("POST", "/api/v1/user/delete", json={"user_ids": [profile_id]})


class AsyncLegacyProfilesAPI:
    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def create(self, *, group_id: str = "0", **fields: Any) -> Profile:
        payload = _compact({"group_id": group_id, **fields})
        data = await self._transport.request("POST", "/api/v1/user/create", json=payload)
        profile_id = data.get("id") if isinstance(data, Mapping) else None
        return Profile.from_api({"user_id": profile_id, **(dict(data) if isinstance(data, Mapping) else {})})

    async def list(self, **filters: Any) -> list[Profile]:
        data = await self._transport.request("GET", "/api/v1/user/list", params=_compact(filters))
        return [Profile.from_api(item) for item in _items(data)]

    async def delete(self, profile_id: str) -> None:
        await self._transport.request("POST", "/api/v1/user/delete", json={"user_ids": [profile_id]})


class LegacyV1:
    def __init__(self, transport: Any) -> None:
        self.profiles = LegacyProfilesAPI(transport)


class AsyncLegacyV1:
    def __init__(self, transport: Any) -> None:
        self.profiles = AsyncLegacyProfilesAPI(transport)

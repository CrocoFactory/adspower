from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal, overload

from .exceptions import AdsPowerResponseError, AdsPowerValidationError, ProfileNotFoundError
from .models import BrowserConnection, BrowserStatus, Category, Group, Profile, ProfileSelector, Proxy, RunningBrowser
from .types import AdsPowerBool, CacheType


def _compact(data: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


def _response_error(message: str, *, method: str, path: str) -> AdsPowerResponseError:
    return AdsPowerResponseError(f"{message} ({method} {path})", method=method, path=path)


def _expect_mapping(data: Any, *, method: str, path: str) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise _response_error("AdsPower returned a non-object typed response", method=method, path=path)
    return data


def _items(
    data: Any,
    *,
    keys: tuple[str, ...],
    method: str,
    path: str,
) -> list[Mapping[str, Any]]:
    if isinstance(data, list):
        items = data
    elif isinstance(data, Mapping):
        found = False
        items: Any = None
        for key in keys:
            if key in data:
                found = True
                items = data[key]
                break
        if not found:
            raise _response_error(
                f"AdsPower response is missing the expected list field ({', '.join(keys)})",
                method=method,
                path=path,
            )
        if not isinstance(items, list):
            raise _response_error("AdsPower returned a malformed list field", method=method, path=path)
    else:
        raise _response_error("AdsPower returned a malformed list response", method=method, path=path)

    if not all(isinstance(item, Mapping) for item in items):
        raise _response_error("AdsPower returned a malformed item in a typed list", method=method, path=path)
    return list(items)


def _parse_model(factory: Any, data: Any, *, method: str, path: str) -> Any:
    mapping = _expect_mapping(data, method=method, path=path)
    try:
        return factory(mapping)
    except AdsPowerResponseError as exc:
        raise AdsPowerResponseError(
            f"{exc} ({method} {path})",
            code=exc.code,
            response=exc.response,
            method=method,
            path=path,
        ) from exc


def _parse_models(factory: Any, items: list[Mapping[str, Any]], *, method: str, path: str) -> list[Any]:
    return [_parse_model(factory, item, method=method, path=path) for item in items]


def _validate_page(page: int, *, name: str = "page") -> None:
    if page < 1:
        raise AdsPowerValidationError(f"{name} must be >= 1")


def _validate_max_pages(max_pages: int | None) -> None:
    if max_pages is not None and max_pages < 1:
        raise AdsPowerValidationError("max_pages must be >= 1")


def _v2_list_payload(page: int, page_size: int, filters: Mapping[str, Any]) -> dict[str, Any]:
    request_filters = dict(filters)
    for key in ("profile_id", "profile_no"):
        if key in request_filters and isinstance(request_filters[key], str):
            request_filters[key] = [request_filters[key]]
    return _compact({"page": page, "limit": page_size, **request_filters})


def _require_sequence(value: Sequence[Any], *, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)):
        raise AdsPowerValidationError(f"{name} must be a sequence of values, not a string")
    return value


def _ids(values: Sequence[str], *, name: str, maximum: int | None = None) -> list[str]:
    _require_sequence(values, name=name)
    result = [str(value) for value in values]
    if not result:
        raise AdsPowerValidationError(f"{name} must contain at least 1 item")
    if maximum is not None and len(result) > maximum:
        raise AdsPowerValidationError(f"{name} must contain between 1 and {maximum} items")
    return result


def _selector(profile_id: str | None = None, profile_no: str | None = None) -> ProfileSelector:
    return ProfileSelector(profile_id=profile_id, profile_no=profile_no)


def _cookies(data: Any) -> list[dict[str, Any]]:
    method, path = "GET", "/api/v2/browser-profile/cookies"
    mapping = _expect_mapping(data, method=method, path=path)
    value = mapping.get("cookies", mapping.get("cookie", mapping))
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise _response_error("AdsPower returned invalid cookie JSON", method=method, path=path) from exc
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise _response_error("AdsPower returned cookies in an unsupported format", method=method, path=path)
    return [dict(item) for item in value]


def _profile_default_fields(fields: dict[str, Any]) -> None:
    if fields.get("proxyid") is None and fields.get("user_proxy_config") is None:
        fields["user_proxy_config"] = {"proxy_soft": "no_proxy"}
    if fields.get("fingerprint_config") is None:
        fields["fingerprint_config"] = {
            "automatic_timezone": "1",
            "language": ["en-US", "en"],
            "flash": "block",
            "webrtc": "disabled",
        }


def _prepare_user_proxy_config(fields: dict[str, Any]) -> None:
    value = fields.get("user_proxy_config")
    if value is None:
        return
    if not isinstance(value, Mapping):
        raise AdsPowerValidationError("user_proxy_config must be a mapping")
    legacy = {"soft", "type", "host", "port", "user", "password"}.intersection(value)
    if legacy:
        names = ", ".join(sorted(legacy))
        raise AdsPowerValidationError(
            f"legacy user_proxy_config keys are not supported in v3: {names}; use proxy_* keys"
        )
    normalized = dict(value)
    if normalized.get("proxy_port") is not None:
        normalized["proxy_port"] = str(normalized["proxy_port"])
    fields["user_proxy_config"] = normalized


def _serialize_proxy_fields(fields: Mapping[str, Any], *, require_type: bool = False) -> dict[str, Any]:
    item = dict(fields)
    public_type = item.pop("proxy_type", None)
    legacy_type = item.get("type")
    if public_type is not None and legacy_type is not None and public_type != legacy_type:
        raise AdsPowerValidationError("proxy_type and legacy type specify different values")
    if public_type is not None:
        item["type"] = public_type
    if require_type and item.get("type") is None:
        raise AdsPowerValidationError("proxy_type is required")
    if item.get("port") is not None:
        item["port"] = str(item["port"])
    return _compact(item)


def _extract_proxy_ids(data: Any) -> list[str]:
    method, path = "POST", "/api/v2/proxy-list/create"
    if isinstance(data, Mapping):
        ids: Any = data.get("proxy_id")
        if ids is None:
            ids = data.get("proxy_ids")
        if ids is None:
            ids = data.get("id")
    else:
        ids = data

    if isinstance(ids, list):
        values = ids
    elif ids not in (None, ""):
        values = [ids]
    else:
        raise _response_error("AdsPower proxy-create response does not contain a proxy id", method=method, path=path)

    if any(value in (None, "") for value in values):
        raise _response_error("AdsPower proxy-create response contains an invalid proxy id", method=method, path=path)
    return [str(value) for value in values]


def _serialize_ads_power_bool(value: bool | AdsPowerBool, *, name: str) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if value in (0, 1, "0", "1"):
        return str(value)
    raise AdsPowerValidationError(f"{name} must be a bool, 0/1, or '0'/'1'")


def build_browser_start_payload(
    selector: ProfileSelector,
    *,
    headless: bool = False,
    start_maximized: bool = False,
    launch_args: Sequence[str] | None = None,
    last_opened_tabs: bool | AdsPowerBool | None = None,
    proxy_detection: bool | AdsPowerBool | None = None,
    password_filling: bool | AdsPowerBool | None = None,
    password_saving: bool | AdsPowerBool | None = None,
    cdp_mask: bool | AdsPowerBool | None = None,
    delete_cache: bool | AdsPowerBool | None = None,
    device_scale: float | int | str | None = None,
    extra_options: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one documented Browser Start V2 payload shared by sync and async clients."""
    if launch_args is not None:
        _require_sequence(launch_args, name="launch_args")
    normalized_launch_args = [str(arg) for arg in (launch_args or [])]
    if (
        start_maximized
        and "--start-maximized" not in normalized_launch_args
        and not any(arg.startswith("--window-size=") for arg in normalized_launch_args)
    ):
        normalized_launch_args.append("--start-maximized")

    payload: dict[str, Any] = {
        **selector.payload,
        "headless": "1" if headless else "0",
    }
    if normalized_launch_args:
        payload["launch_args"] = normalized_launch_args

    typed_flags: dict[str, bool | AdsPowerBool | None] = {
        "last_opened_tabs": last_opened_tabs,
        "proxy_detection": proxy_detection,
        "password_filling": password_filling,
        "password_saving": password_saving,
        "cdp_mask": cdp_mask,
        "delete_cache": delete_cache,
    }
    for name, value in typed_flags.items():
        if value is not None:
            payload[name] = _serialize_ads_power_bool(value, name=name)

    if device_scale is not None:
        payload["device_scale"] = device_scale

    extras = dict(extra_options or {})
    collisions = sorted(set(payload).intersection(extras))
    if collisions:
        raise AdsPowerValidationError(
            f"extra_options duplicates typed browser options: {', '.join(collisions)}"
        )
    payload.update(extras)
    return payload


class ProfilesAPI:
    """Synchronous typed browser-profile operations."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def create(self, *, name: str | None = None, group_id: str = "0", **fields: Any) -> Profile:
        """Create a profile and parse the profile returned by AdsPower."""
        _profile_default_fields(fields)
        _prepare_user_proxy_config(fields)
        path = "/api/v2/browser-profile/create"
        data = self._transport.request(
            "POST",
            path,
            json=_compact({"name": name, "group_id": group_id, **fields}),
        )
        return _parse_model(Profile.from_api, data, method="POST", path=path)

    @overload
    def update(self, profile_id: str, *, refresh: Literal[False] = False, **fields: Any) -> None: ...

    @overload
    def update(self, profile_id: str, *, refresh: Literal[True], **fields: Any) -> Profile: ...

    def update(self, profile_id: str, *, refresh: bool = False, **fields: Any) -> Profile | None:
        """Update a profile; fetch and return it only when `refresh=True`."""
        _prepare_user_proxy_config(fields)
        self._transport.request(
            "POST",
            "/api/v2/browser-profile/update",
            json=_compact({"profile_id": profile_id, **fields}),
        )
        return self.get(profile_id) if refresh else None

    def list(
        self,
        *,
        group_id: str | None = None,
        profile_id: Sequence[str] | str | None = None,
        profile_no: Sequence[str] | str | None = None,
        sort_type: str | None = None,
        sort_order: str | None = None,
        page: int = 1,
        page_size: int = 100,
        extra_filters: Mapping[str, Any] | None = None,
    ) -> list[Profile]:
        """List profiles using documented Query Profile V2 filters."""
        _validate_page(page)
        if not 1 <= page_size <= 100:
            raise AdsPowerValidationError("profile page_size must be between 1 and 100")
        filters = {
            "group_id": group_id,
            "profile_id": profile_id,
            "profile_no": profile_no,
            "sort_type": sort_type,
            "sort_order": sort_order,
            **dict(extra_filters or {}),
        }
        if {"name", "name_filter"}.intersection(filters):
            raise AdsPowerValidationError(
                "name/name_filter are not documented Query Profile V2 fields; use find_by_name()"
            )
        path = "/api/v2/browser-profile/list"
        data = self._transport.request("POST", path, json=_v2_list_payload(page, page_size, filters))
        items = _items(data, keys=("list", "profiles", "items"), method="POST", path=path)
        return _parse_models(Profile.from_api, items, method="POST", path=path)

    def find_by_name(
        self,
        name: str,
        *,
        group_id: str | None = None,
        page_size: int = 100,
        max_pages: int | None = None,
    ) -> Profile | None:
        """Find the first exact profile-name match using documented list requests."""
        matches = self.find_all_by_name(
            name,
            group_id=group_id,
            page_size=page_size,
            max_pages=max_pages,
        )
        return matches[0] if matches else None

    def find_all_by_name(
        self,
        name: str,
        *,
        group_id: str | None = None,
        page_size: int = 100,
        max_pages: int | None = None,
    ) -> list[Profile]:
        """Find all exact profile-name matches client-side across list pages."""
        _validate_max_pages(max_pages)
        page, matches = 1, []
        while max_pages is None or page <= max_pages:
            profiles = self.list(group_id=group_id, page=page, page_size=page_size)
            matches.extend(profile for profile in profiles if profile.name == name)
            if len(profiles) < page_size:
                break
            page += 1
        return matches

    def get(self, profile_id: str) -> Profile:
        """Return one profile by id or raise `ProfileNotFoundError`."""
        profiles = self.list(profile_id=profile_id, page_size=1)
        if not profiles:
            path = "/api/v2/browser-profile/list"
            raise ProfileNotFoundError(
                f"Profile {profile_id!r} was not found (POST {path})",
                method="POST",
                path=path,
            )
        return profiles[0]

    def delete(self, profile_id: str) -> None:
        """Delete one browser profile."""
        self.delete_many([profile_id])

    def delete_many(self, profile_ids: Sequence[str]) -> None:
        """Delete up to the documented 100 profiles in one request."""
        self._transport.request(
            "POST",
            "/api/v2/browser-profile/delete",
            json={"profile_id": _ids(profile_ids, name="profile_ids", maximum=100)},
        )

    def move(self, profile_ids: Sequence[str], group_id: str) -> None:
        """Move profiles to a group without imposing an undocumented local batch maximum."""
        self._transport.request(
            "POST",
            "/api/v1/user/regroup",
            json={"user_ids": _ids(profile_ids, name="profile_ids"), "group_id": str(group_id)},
        )

    def delete_cache(self, profile_ids: Sequence[str], cache_types: Sequence[CacheType | str]) -> None:
        """Delete selected cache types without imposing an undocumented local batch maximum."""
        _require_sequence(cache_types, name="cache_types")
        self._transport.request(
            "POST",
            "/api/v2/browser-profile/delete-cache",
            json={
                "profile_id": _ids(profile_ids, name="profile_ids"),
                "type": [str(item) for item in cache_types],
            },
        )

    def cookies(
        self,
        *,
        profile_id: str | None = None,
        profile_no: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return cookies for exactly one profile selector."""
        data = self._transport.request(
            "GET",
            "/api/v2/browser-profile/cookies",
            params=_selector(profile_id, profile_no).payload,
        )
        return _cookies(data)

    def share(
        self,
        profile_ids: Sequence[str],
        receiver: str,
        *,
        content: Sequence[str] | None = None,
        share_type: int = 1,
    ) -> dict[str, Any]:
        """Share profiles using the documented share type and 200-profile maximum."""
        if share_type not in {1, 2}:
            raise AdsPowerValidationError("share_type must be 1 or 2")
        if content is not None:
            _require_sequence(content, name="content")
        data = self._transport.request(
            "POST",
            "/api/v2/browser-profile/share",
            json=_compact(
                {
                    "profile_id": _ids(profile_ids, name="profile_ids", maximum=200),
                    "receiver": receiver,
                    "content": list(content) if content is not None else None,
                    "share_type": share_type,
                }
            ),
        )
        return dict(data) if isinstance(data, Mapping) else {"data": data}


class AsyncProfilesAPI:
    """Asynchronous typed browser-profile operations."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def create(self, *, name: str | None = None, group_id: str = "0", **fields: Any) -> Profile:
        """Create a profile and parse the profile returned by AdsPower."""
        _profile_default_fields(fields)
        _prepare_user_proxy_config(fields)
        path = "/api/v2/browser-profile/create"
        data = await self._transport.request(
            "POST",
            path,
            json=_compact({"name": name, "group_id": group_id, **fields}),
        )
        return _parse_model(Profile.from_api, data, method="POST", path=path)

    @overload
    async def update(
        self,
        profile_id: str,
        *,
        refresh: Literal[False] = False,
        **fields: Any,
    ) -> None: ...

    @overload
    async def update(
        self,
        profile_id: str,
        *,
        refresh: Literal[True],
        **fields: Any,
    ) -> Profile: ...

    async def update(self, profile_id: str, *, refresh: bool = False, **fields: Any) -> Profile | None:
        """Update a profile; fetch and return it only when `refresh=True`."""
        _prepare_user_proxy_config(fields)
        await self._transport.request(
            "POST",
            "/api/v2/browser-profile/update",
            json=_compact({"profile_id": profile_id, **fields}),
        )
        return await self.get(profile_id) if refresh else None

    async def list(
        self,
        *,
        group_id: str | None = None,
        profile_id: Sequence[str] | str | None = None,
        profile_no: Sequence[str] | str | None = None,
        sort_type: str | None = None,
        sort_order: str | None = None,
        page: int = 1,
        page_size: int = 100,
        extra_filters: Mapping[str, Any] | None = None,
    ) -> list[Profile]:
        """List profiles using documented Query Profile V2 filters."""
        _validate_page(page)
        if not 1 <= page_size <= 100:
            raise AdsPowerValidationError("profile page_size must be between 1 and 100")
        filters = {
            "group_id": group_id,
            "profile_id": profile_id,
            "profile_no": profile_no,
            "sort_type": sort_type,
            "sort_order": sort_order,
            **dict(extra_filters or {}),
        }
        if {"name", "name_filter"}.intersection(filters):
            raise AdsPowerValidationError(
                "name/name_filter are not documented Query Profile V2 fields; use find_by_name()"
            )
        path = "/api/v2/browser-profile/list"
        data = await self._transport.request("POST", path, json=_v2_list_payload(page, page_size, filters))
        items = _items(data, keys=("list", "profiles", "items"), method="POST", path=path)
        return _parse_models(Profile.from_api, items, method="POST", path=path)

    async def find_by_name(
        self,
        name: str,
        *,
        group_id: str | None = None,
        page_size: int = 100,
        max_pages: int | None = None,
    ) -> Profile | None:
        """Find the first exact profile-name match using documented list requests."""
        matches = await self.find_all_by_name(
            name,
            group_id=group_id,
            page_size=page_size,
            max_pages=max_pages,
        )
        return matches[0] if matches else None

    async def find_all_by_name(
        self,
        name: str,
        *,
        group_id: str | None = None,
        page_size: int = 100,
        max_pages: int | None = None,
    ) -> list[Profile]:
        """Find all exact profile-name matches client-side across list pages."""
        _validate_max_pages(max_pages)
        page, matches = 1, []
        while max_pages is None or page <= max_pages:
            profiles = await self.list(group_id=group_id, page=page, page_size=page_size)
            matches.extend(profile for profile in profiles if profile.name == name)
            if len(profiles) < page_size:
                break
            page += 1
        return matches

    async def get(self, profile_id: str) -> Profile:
        """Return one profile by id or raise `ProfileNotFoundError`."""
        profiles = await self.list(profile_id=profile_id, page_size=1)
        if not profiles:
            path = "/api/v2/browser-profile/list"
            raise ProfileNotFoundError(
                f"Profile {profile_id!r} was not found (POST {path})",
                method="POST",
                path=path,
            )
        return profiles[0]

    async def delete(self, profile_id: str) -> None:
        """Delete one browser profile."""
        await self.delete_many([profile_id])

    async def delete_many(self, profile_ids: Sequence[str]) -> None:
        """Delete up to the documented 100 profiles in one request."""
        await self._transport.request(
            "POST",
            "/api/v2/browser-profile/delete",
            json={"profile_id": _ids(profile_ids, name="profile_ids", maximum=100)},
        )

    async def move(self, profile_ids: Sequence[str], group_id: str) -> None:
        """Move profiles to a group without imposing an undocumented local batch maximum."""
        await self._transport.request(
            "POST",
            "/api/v1/user/regroup",
            json={"user_ids": _ids(profile_ids, name="profile_ids"), "group_id": str(group_id)},
        )

    async def delete_cache(
        self,
        profile_ids: Sequence[str],
        cache_types: Sequence[CacheType | str],
    ) -> None:
        """Delete selected cache types without imposing an undocumented local batch maximum."""
        _require_sequence(cache_types, name="cache_types")
        await self._transport.request(
            "POST",
            "/api/v2/browser-profile/delete-cache",
            json={
                "profile_id": _ids(profile_ids, name="profile_ids"),
                "type": [str(item) for item in cache_types],
            },
        )

    async def cookies(
        self,
        *,
        profile_id: str | None = None,
        profile_no: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return cookies for exactly one profile selector."""
        data = await self._transport.request(
            "GET",
            "/api/v2/browser-profile/cookies",
            params=_selector(profile_id, profile_no).payload,
        )
        return _cookies(data)

    async def share(
        self,
        profile_ids: Sequence[str],
        receiver: str,
        *,
        content: Sequence[str] | None = None,
        share_type: int = 1,
    ) -> dict[str, Any]:
        """Share profiles using the documented share type and 200-profile maximum."""
        if share_type not in {1, 2}:
            raise AdsPowerValidationError("share_type must be 1 or 2")
        if content is not None:
            _require_sequence(content, name="content")
        data = await self._transport.request(
            "POST",
            "/api/v2/browser-profile/share",
            json=_compact(
                {
                    "profile_id": _ids(profile_ids, name="profile_ids", maximum=200),
                    "receiver": receiver,
                    "content": list(content) if content is not None else None,
                    "share_type": share_type,
                }
            ),
        )
        return dict(data) if isinstance(data, Mapping) else {"data": data}


class GroupsAPI:
    """Synchronous group operations."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def create(self, name: str, remark: str | None = None) -> Group:
        """Create a group."""
        path = "/api/v1/group/create"
        data = self._transport.request(
            "POST",
            path,
            json=_compact({"group_name": name, "remark": remark}),
        )
        return _parse_model(Group.from_api, data, method="POST", path=path)

    def list(self, *, name: str | None = None, page: int = 1, page_size: int = 100) -> list[Group]:
        """List groups with documented pagination."""
        _validate_page(page)
        if not 1 <= page_size <= 2000:
            raise AdsPowerValidationError("group page_size must be between 1 and 2000")
        path = "/api/v1/group/list"
        data = self._transport.request(
            "GET",
            path,
            params=_compact({"group_name": name, "page": page, "page_size": page_size}),
        )
        items = _items(data, keys=("list", "items"), method="GET", path=path)
        return _parse_models(Group.from_api, items, method="GET", path=path)

    def update(self, group_id: str, *, name: str, remark: str | None = None) -> Group:
        """Update a group and return the deterministic local representation."""
        self._transport.request(
            "POST",
            "/api/v1/group/update",
            json=_compact({"group_id": group_id, "group_name": name, "remark": remark}),
        )
        return Group(id=group_id, name=name, remark=remark)


class AsyncGroupsAPI:
    """Asynchronous group operations."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def create(self, name: str, remark: str | None = None) -> Group:
        """Create a group."""
        path = "/api/v1/group/create"
        data = await self._transport.request(
            "POST",
            path,
            json=_compact({"group_name": name, "remark": remark}),
        )
        return _parse_model(Group.from_api, data, method="POST", path=path)

    async def list(
        self,
        *,
        name: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> list[Group]:
        """List groups with documented pagination."""
        _validate_page(page)
        if not 1 <= page_size <= 2000:
            raise AdsPowerValidationError("group page_size must be between 1 and 2000")
        path = "/api/v1/group/list"
        data = await self._transport.request(
            "GET",
            path,
            params=_compact({"group_name": name, "page": page, "page_size": page_size}),
        )
        items = _items(data, keys=("list", "items"), method="GET", path=path)
        return _parse_models(Group.from_api, items, method="GET", path=path)

    async def update(self, group_id: str, *, name: str, remark: str | None = None) -> Group:
        """Update a group and return the deterministic local representation."""
        await self._transport.request(
            "POST",
            "/api/v1/group/update",
            json=_compact({"group_id": group_id, "group_name": name, "remark": remark}),
        )
        return Group(id=group_id, name=name, remark=remark)


class ProxiesAPI:
    """Synchronous stored-proxy operations."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def create(
        self,
        *,
        proxy_type: str | None = None,
        host: str,
        port: str | int,
        user: str | None = None,
        password: str | None = None,
        **fields: Any,
    ) -> list[str]:
        """Create a stored proxy; `proxy_type` is serialized as AdsPower's `type` key."""
        if "type" in fields:
            legacy_type = fields.pop("type")
            if proxy_type is not None and proxy_type != legacy_type:
                raise AdsPowerValidationError("proxy_type and legacy type specify different values")
            proxy_type = str(legacy_type)
        return self.create_many(
            [
                {
                    **fields,
                    "proxy_type": proxy_type,
                    "host": host,
                    "port": port,
                    "user": user,
                    "password": password,
                }
            ]
        )

    def create_many(self, proxies: Sequence[Mapping[str, Any]]) -> list[str]:
        """Create up to the documented 500 stored proxies."""
        _require_sequence(proxies, name="proxies")
        if not 1 <= len(proxies) <= 500:
            raise AdsPowerValidationError("proxies must contain between 1 and 500 items")
        items: list[dict[str, Any]] = []
        for index, proxy in enumerate(proxies):
            if not isinstance(proxy, Mapping):
                raise AdsPowerValidationError(f"proxies[{index}] must be a mapping")
            items.append(_serialize_proxy_fields(proxy, require_type=True))
        data = self._transport.request("POST", "/api/v2/proxy-list/create", json=items)
        return _extract_proxy_ids(data)

    def update(self, proxy_id: str, *, proxy_type: str | None = None, **fields: Any) -> None:
        """Update a stored proxy using the same serialization rules as creation."""
        if proxy_type is not None:
            fields["proxy_type"] = proxy_type
        payload = _serialize_proxy_fields(fields)
        self._transport.request(
            "POST",
            "/api/v2/proxy-list/update",
            json={"proxy_id": str(proxy_id), **payload},
        )

    def delete(self, proxy_id: str) -> None:
        """Delete one stored proxy."""
        self.delete_many([proxy_id])

    def delete_many(self, proxy_ids: Sequence[str]) -> None:
        """Delete up to the documented 100 stored proxies."""
        self._transport.request(
            "POST",
            "/api/v2/proxy-list/delete",
            json={"proxy_id": _ids(proxy_ids, name="proxy_ids", maximum=100)},
        )

    def list(
        self,
        *,
        proxy_ids: Sequence[str] | str | None = None,
        page: int = 1,
        page_size: int = 50,
        **filters: Any,
    ) -> list[Proxy]:
        """List stored proxies with documented pagination and id filtering."""
        _validate_page(page)
        if not 1 <= page_size <= 200:
            raise AdsPowerValidationError("proxy page_size must be between 1 and 200")
        if isinstance(proxy_ids, str):
            proxy_ids = [proxy_ids]
        if proxy_ids is not None:
            filters["proxy_id"] = _ids(proxy_ids, name="proxy_ids", maximum=100)
        path = "/api/v2/proxy-list/list"
        data = self._transport.request(
            "POST",
            path,
            json={"page": page, "limit": page_size, **filters},
        )
        items = _items(data, keys=("list", "proxy_list", "items"), method="POST", path=path)
        return _parse_models(Proxy.from_api, items, method="POST", path=path)


class AsyncProxiesAPI:
    """Asynchronous stored-proxy operations."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def create(
        self,
        *,
        proxy_type: str | None = None,
        host: str,
        port: str | int,
        user: str | None = None,
        password: str | None = None,
        **fields: Any,
    ) -> list[str]:
        """Create a stored proxy; `proxy_type` is serialized as AdsPower's `type` key."""
        if "type" in fields:
            legacy_type = fields.pop("type")
            if proxy_type is not None and proxy_type != legacy_type:
                raise AdsPowerValidationError("proxy_type and legacy type specify different values")
            proxy_type = str(legacy_type)
        return await self.create_many(
            [
                {
                    **fields,
                    "proxy_type": proxy_type,
                    "host": host,
                    "port": port,
                    "user": user,
                    "password": password,
                }
            ]
        )

    async def create_many(self, proxies: Sequence[Mapping[str, Any]]) -> list[str]:
        """Create up to the documented 500 stored proxies."""
        _require_sequence(proxies, name="proxies")
        if not 1 <= len(proxies) <= 500:
            raise AdsPowerValidationError("proxies must contain between 1 and 500 items")
        items: list[dict[str, Any]] = []
        for index, proxy in enumerate(proxies):
            if not isinstance(proxy, Mapping):
                raise AdsPowerValidationError(f"proxies[{index}] must be a mapping")
            items.append(_serialize_proxy_fields(proxy, require_type=True))
        data = await self._transport.request("POST", "/api/v2/proxy-list/create", json=items)
        return _extract_proxy_ids(data)

    async def update(self, proxy_id: str, *, proxy_type: str | None = None, **fields: Any) -> None:
        """Update a stored proxy using the same serialization rules as creation."""
        if proxy_type is not None:
            fields["proxy_type"] = proxy_type
        payload = _serialize_proxy_fields(fields)
        await self._transport.request(
            "POST",
            "/api/v2/proxy-list/update",
            json={"proxy_id": str(proxy_id), **payload},
        )

    async def delete(self, proxy_id: str) -> None:
        """Delete one stored proxy."""
        await self.delete_many([proxy_id])

    async def delete_many(self, proxy_ids: Sequence[str]) -> None:
        """Delete up to the documented 100 stored proxies."""
        await self._transport.request(
            "POST",
            "/api/v2/proxy-list/delete",
            json={"proxy_id": _ids(proxy_ids, name="proxy_ids", maximum=100)},
        )

    async def list(
        self,
        *,
        proxy_ids: Sequence[str] | str | None = None,
        page: int = 1,
        page_size: int = 50,
        **filters: Any,
    ) -> list[Proxy]:
        """List stored proxies with documented pagination and id filtering."""
        _validate_page(page)
        if not 1 <= page_size <= 200:
            raise AdsPowerValidationError("proxy page_size must be between 1 and 200")
        if isinstance(proxy_ids, str):
            proxy_ids = [proxy_ids]
        if proxy_ids is not None:
            filters["proxy_id"] = _ids(proxy_ids, name="proxy_ids", maximum=100)
        path = "/api/v2/proxy-list/list"
        data = await self._transport.request(
            "POST",
            path,
            json={"page": page, "limit": page_size, **filters},
        )
        items = _items(data, keys=("list", "proxy_list", "items"), method="POST", path=path)
        return _parse_models(Proxy.from_api, items, method="POST", path=path)


class CategoriesAPI:
    """Synchronous browser-profile category operations."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def list(
        self,
        *,
        category_id: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> list[Category]:
        """List categories with documented pagination."""
        _validate_page(page)
        if not 1 <= page_size <= 100:
            raise AdsPowerValidationError("category page_size must be between 1 and 100")
        path = "/api/v2/category/list"
        data = self._transport.request(
            "GET",
            path,
            params=_compact({"category_id": category_id, "page": page, "limit": page_size}),
        )
        items = _items(data, keys=("list", "category_list", "items"), method="GET", path=path)
        return _parse_models(Category.from_api, items, method="GET", path=path)


class AsyncCategoriesAPI:
    """Asynchronous browser-profile category operations."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def list(
        self,
        *,
        category_id: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> list[Category]:
        """List categories with documented pagination."""
        _validate_page(page)
        if not 1 <= page_size <= 100:
            raise AdsPowerValidationError("category page_size must be between 1 and 100")
        path = "/api/v2/category/list"
        data = await self._transport.request(
            "GET",
            path,
            params=_compact({"category_id": category_id, "page": page, "limit": page_size}),
        )
        items = _items(data, keys=("list", "category_list", "items"), method="GET", path=path)
        return _parse_models(Category.from_api, items, method="GET", path=path)


class HealthAPI:
    """Synchronous explicit Local API health check."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def check(self) -> Any:
        """Request AdsPower's explicit status endpoint."""
        return self._transport.request("GET", "/status")


class AsyncHealthAPI:
    """Asynchronous explicit Local API health check."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def check(self) -> Any:
        """Request AdsPower's explicit status endpoint."""
        return await self._transport.request("GET", "/status")


def parse_browser_connection(
    data: Any,
    base_url: str,
    *,
    browser_host: str | None = None,
    endpoint_policy: str = "rewrite_loopback_to_api_host",
) -> BrowserConnection:
    path = "/api/v2/browser-profile/start"
    mapping = _expect_mapping(data, method="POST", path=path)
    try:
        return BrowserConnection.from_api(
            mapping,
            base_url=base_url,
            browser_host=browser_host,
            endpoint_policy=endpoint_policy,
        )
    except AdsPowerResponseError as exc:
        raise AdsPowerResponseError(
            f"{exc} (POST {path})",
            method="POST",
            path=path,
        ) from exc


def parse_browser_status(
    data: Any,
    base_url: str,
    *,
    browser_host: str | None = None,
    endpoint_policy: str = "rewrite_loopback_to_api_host",
) -> BrowserStatus:
    path = "/api/v2/browser-profile/active"
    mapping = _expect_mapping(data, method="GET", path=path)
    status = str(mapping.get("status", mapping.get("state", "inactive")))
    connection_keys = {
        "ws",
        "debug_port",
        "webdriver",
        "selenium",
        "playwright_cdp",
        "marionette_port",
        "marionette_host",
    }
    connection = None
    if connection_keys.intersection(mapping):
        try:
            connection = BrowserConnection.from_api(
                mapping,
                base_url=base_url,
                browser_host=browser_host,
                endpoint_policy=endpoint_policy,
            )
        except AdsPowerResponseError as exc:
            raise AdsPowerResponseError(
                f"{exc} (GET {path})",
                method="GET",
                path=path,
            ) from exc
    known = {"status", "state", *connection_keys}
    return BrowserStatus(
        status=status,
        connection=connection,
        extra={key: value for key, value in mapping.items() if key not in known},
    )


def parse_running_browsers(
    data: Any,
    base_url: str,
    *,
    browser_host: str | None = None,
    endpoint_policy: str = "rewrite_loopback_to_api_host",
) -> list[RunningBrowser]:
    method, path = "GET", "/api/v1/browser/local-active"
    items = _items(data, keys=("list", "active", "items"), method=method, path=path)
    result: list[RunningBrowser] = []
    connection_known = {
        "ws",
        "debug_port",
        "webdriver",
        "selenium",
        "playwright_cdp",
        "marionette_port",
        "marionette_host",
    }
    for item in items:
        profile_id = item.get("profile_id")
        if profile_id is None:
            profile_id = item.get("user_id")
        if profile_id in (None, ""):
            raise _response_error(
                "Active-browser response item does not contain a profile id",
                method=method,
                path=path,
            )
        try:
            connection = BrowserConnection.from_api(
                item,
                base_url=base_url,
                browser_host=browser_host,
                endpoint_policy=endpoint_policy,
            )
        except AdsPowerResponseError as exc:
            raise AdsPowerResponseError(
                f"{exc} ({method} {path})",
                method=method,
                path=path,
            ) from exc
        known = {"profile_id", "user_id", *connection_known}
        result.append(
            RunningBrowser(
                profile_id=str(profile_id),
                connection=connection,
                extra={key: value for key, value in item.items() if key not in known},
            )
        )
    return result

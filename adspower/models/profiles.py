from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping

from .._json import JsonObject, JsonValue, collect_extra, first_present, optional_id_string, optional_string, require_id_string, require_object
from .._security import redact_sensitive


@dataclass(frozen=True, slots=True)
class CreatedProfile:
    profile_id: str
    profile_no: str | None = None


@dataclass(frozen=True, slots=True, repr=False)
class Profile:
    profile_id: str
    profile_no: str | None = None
    name: str | None = None
    group_id: str | None = None
    group_name: str | None = None
    platform: str | None = None
    username: str | None = None
    remark: str | None = None
    category_id: str | None = None
    created_time: str | None = None
    last_open_time: str | None = None
    user_proxy_config: Mapping[str, JsonValue] | None = None
    extra: Mapping[str, JsonValue] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Profile({redact_sensitive({
            'profile_id': self.profile_id, 'profile_no': self.profile_no, 'name': self.name,
            'group_id': self.group_id, 'group_name': self.group_name, 'platform': self.platform,
            'username': self.username, 'remark': self.remark, 'category_id': self.category_id,
            'created_time': self.created_time, 'last_open_time': self.last_open_time,
            'user_proxy_config': self.user_proxy_config, 'extra': self.extra,
        })!r})"


@dataclass(frozen=True, slots=True)
class Group:
    group_id: str
    name: str | None = None
    remark: str | None = None
    extra: Mapping[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Category:
    category_id: str
    name: str | None = None
    remark: str | None = None
    extra: Mapping[str, JsonValue] = field(default_factory=dict)


def parse_created_profile(value: object) -> CreatedProfile:
    data = require_object(value, field="created profile")
    profile_id = require_id_string(first_present(data, "profile_id", "user_id", "id"), field="profile_id")
    return CreatedProfile(profile_id, optional_id_string(first_present(data, "profile_no", "serial_number"), field="profile_no"))


def parse_profile(value: object) -> Profile:
    data = require_object(value, field="profile")
    known = {
        "profile_id", "user_id", "id", "profile_no", "serial_number", "name", "group_id",
        "group_name", "platform", "domain_name", "username", "remark", "category_id",
        "created_time", "last_open_time", "user_proxy_config",
    }
    proxy = data.get("user_proxy_config")
    proxy_object = require_object(proxy, field="user_proxy_config") if proxy is not None else None
    return Profile(
        profile_id=require_id_string(first_present(data, "profile_id", "user_id", "id"), field="profile_id"),
        profile_no=optional_id_string(first_present(data, "profile_no", "serial_number"), field="profile_no"),
        name=optional_string(data.get("name"), field="name"),
        group_id=optional_id_string(data.get("group_id"), field="group_id"),
        group_name=optional_string(data.get("group_name"), field="group_name"),
        platform=optional_string(first_present(data, "platform", "domain_name"), field="platform"),
        username=optional_string(data.get("username"), field="username"),
        remark=optional_string(data.get("remark"), field="remark"),
        category_id=optional_id_string(data.get("category_id"), field="category_id"),
        created_time=optional_string(data.get("created_time"), field="created_time"),
        last_open_time=optional_string(data.get("last_open_time"), field="last_open_time"),
        user_proxy_config=proxy_object,
        extra=collect_extra(data, known),
    )


def _parse_named_resource(value: object, *, kind: str, id_keys: tuple[str, ...], name_keys: tuple[str, ...]):
    data = require_object(value, field=kind)
    resource_id = require_id_string(first_present(data, *id_keys), field=f"{kind}_id")
    name = optional_string(first_present(data, *name_keys), field=f"{kind}_name")
    remark = optional_string(data.get("remark"), field="remark")
    return data, resource_id, name, remark


def parse_group(value: object) -> Group:
    data, resource_id, name, remark = _parse_named_resource(
        value, kind="group", id_keys=("group_id", "id"), name_keys=("group_name", "name")
    )
    return Group(resource_id, name, remark, collect_extra(data, {"group_id", "id", "group_name", "name", "remark"}))


def parse_category(value: object) -> Category:
    data, resource_id, name, remark = _parse_named_resource(
        value, kind="category", id_keys=("category_id", "id"), name_keys=("category_name", "name")
    )
    return Category(resource_id, name, remark, collect_extra(data, {"category_id", "id", "category_name", "name", "remark"}))

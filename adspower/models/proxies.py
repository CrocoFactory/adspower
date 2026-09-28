from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from .._json import (
    JsonObject,
    JsonValue,
    collect_extra,
    first_present,
    optional_int,
    optional_string,
    require_id_string,
    require_list,
    require_object,
)
from .._security import redact_sensitive
from ..errors import AdsPowerValidationError


@dataclass(frozen=True, slots=True)
class StoredProxyConfig:
    proxy_type: Literal["http", "https", "ssh", "socks5"]
    host: str
    port: int | str
    user: str | None = None
    password: str | None = None
    proxy_url: str | None = None
    remark: str | None = None
    ipchecker: Literal["ip2location", "ipapi", "ipfoxy"] | None = None

    def __post_init__(self) -> None:
        try:
            port = int(self.port)
        except (TypeError, ValueError) as exc:
            raise AdsPowerValidationError("proxy port must be an integer") from exc
        if not 0 <= port <= 65536:
            raise AdsPowerValidationError("proxy port must be between 0 and 65536")
        if not self.host:
            raise AdsPowerValidationError("proxy host must not be empty")

    def to_api(self) -> JsonObject:
        values: JsonObject = {
            "type": self.proxy_type,
            "host": self.host,
            "port": str(self.port),
        }
        optional = {
            "user": self.user,
            "password": self.password,
            "proxy_url": self.proxy_url,
            "remark": self.remark,
            "ipchecker": self.ipchecker,
        }
        values.update({key: value for key, value in optional.items() if value is not None})
        return values


@dataclass(frozen=True, slots=True, repr=False)
class Proxy:
    proxy_id: str
    proxy_type: str | None = None
    host: str | None = None
    port: str | None = None
    user: str | None = None
    password: str | None = None
    proxy_url: str | None = None
    remark: str | None = None
    ipchecker: str | None = None
    proxy_partner: str | None = None
    profile_count: int | None = None
    related_profile_no: tuple[str, ...] = ()
    proxy_tags: tuple[Mapping[str, JsonValue], ...] = ()
    extra: Mapping[str, JsonValue] = field(default_factory=dict)

    def __repr__(self) -> str:
        data = {
            "proxy_id": self.proxy_id,
            "proxy_type": self.proxy_type,
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "proxy_url": self.proxy_url,
            "remark": self.remark,
            "ipchecker": self.ipchecker,
            "proxy_partner": self.proxy_partner,
            "profile_count": self.profile_count,
            "related_profile_no": self.related_profile_no,
            "proxy_tags": self.proxy_tags,
            "extra": self.extra,
        }
        return f"Proxy({redact_sensitive(data)!r})"


def parse_proxy(value: object) -> Proxy:
    data = require_object(value, field="proxy")
    related_raw = require_list(data.get("related_profile_no", []), field="related_profile_no")
    related = tuple(require_id_string(item, field="related_profile_no[]") for item in related_raw)
    tags_raw = require_list(data.get("proxy_tags", []), field="proxy_tags")
    tags = tuple(require_object(item, field="proxy_tags[]") for item in tags_raw)
    port = first_present(data, "proxy_port", "port")
    if port is not None and not isinstance(port, (str, int)):
        from ..errors import AdsPowerProtocolError

        raise AdsPowerProtocolError("proxy port must be a string or integer")
    known = {
        "proxy_id",
        "id",
        "proxy_type",
        "type",
        "proxy_host",
        "host",
        "proxy_port",
        "port",
        "proxy_user",
        "user",
        "proxy_password",
        "password",
        "proxy_url",
        "remark",
        "ipchecker",
        "proxy_partner",
        "profile_count",
        "related_profile_no",
        "proxy_tags",
    }
    return Proxy(
        proxy_id=require_id_string(first_present(data, "proxy_id", "id"), field="proxy_id"),
        proxy_type=optional_string(first_present(data, "proxy_type", "type"), field="proxy_type"),
        host=optional_string(first_present(data, "proxy_host", "host"), field="host"),
        port=str(port) if port is not None else None,
        user=optional_string(first_present(data, "proxy_user", "user"), field="user"),
        password=optional_string(
            first_present(data, "proxy_password", "password"),
            field="password",
        ),
        proxy_url=optional_string(data.get("proxy_url"), field="proxy_url"),
        remark=optional_string(data.get("remark"), field="remark"),
        ipchecker=optional_string(data.get("ipchecker"), field="ipchecker"),
        proxy_partner=optional_string(data.get("proxy_partner"), field="proxy_partner"),
        profile_count=optional_int(data.get("profile_count"), field="profile_count"),
        related_profile_no=related,
        proxy_tags=tags,
        extra=collect_extra(data, known),
    )

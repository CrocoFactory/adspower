from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

from .exceptions import AdsPowerValidationError
from .security import redact_sensitive


def _format_host(host: str) -> str:
    """Format a host for an endpoint authority, including IPv6 literals."""
    if ":" in host and not host.startswith("["):
        return f"[{host}]"
    return host


class ProxySoftware(str, Enum):
    BRIGHTDATA = "brightdata"
    BRIGHTAUTO = "brightauto"
    OXYLABS_AUTO = "oxylabsauto"
    NINE_TWO_TWO_S5_AUTO = "922S5auto"
    NINE_TWO_TWO_S5_AUTH = "922S5auth"
    IPFOXY_AUTO = "ipfoxyauto"
    KOOK_AUTO = "kookauto"
    LUMIPROXY_AUTO = "lumiproxyauto"
    SSH = "ssh"
    OTHER = "other"
    NO_PROXY = "no_proxy"


class ScreenResolution:
    @staticmethod
    def fixed(width: int, height: int) -> str:
        if width <= 0 or height <= 0:
            raise ValueError("Screen dimensions must be positive")
        return f"{width}_{height}"


@dataclass(slots=True)
class Profile:
    id: str
    number: str | None = None
    name: str | None = None
    group_id: str | None = None
    group_name: str | None = None
    platform: str | None = None
    username: str | None = None
    remark: str | None = None
    category_id: str | None = None
    created_time: str | None = None
    last_open_time: str | None = None
    user_proxy_config: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: Mapping[str, Any]) -> "Profile":
        profile_id = data.get("profile_id") or data.get("user_id") or data.get("id")
        if profile_id in (None, ""):
            raise ValueError("Profile response does not contain a profile id")
        known = {
            "profile_id", "user_id", "id", "profile_no", "serial_number",
            "name", "group_id", "user_proxy_config",
            "group_name", "platform", "username", "remark", "category_id",
            "created_time", "last_open_time",
        }
        number = data.get("profile_no", data.get("serial_number"))
        return cls(
            id=str(profile_id),
            number=str(number) if number is not None else None,
            name=data.get("name"),
            group_id=str(data["group_id"]) if data.get("group_id") is not None else None,
            group_name=data.get("group_name"),
            platform=data.get("platform", data.get("domain_name")),
            username=data.get("username"),
            remark=data.get("remark"),
            category_id=str(data["category_id"]) if data.get("category_id") is not None else None,
            created_time=str(data["created_time"]) if data.get("created_time") is not None else None,
            last_open_time=str(data["last_open_time"]) if data.get("last_open_time") is not None else None,
            user_proxy_config=data.get("user_proxy_config"),
            extra={key: value for key, value in data.items() if key not in known},
        )

    def __repr__(self) -> str:
        values = {
            "id": self.id,
            "number": self.number,
            "name": self.name,
            "group_id": self.group_id,
            "group_name": self.group_name,
            "platform": self.platform,
            "username": self.username,
            "remark": self.remark,
            "category_id": self.category_id,
            "created_time": self.created_time,
            "last_open_time": self.last_open_time,
            "user_proxy_config": self.user_proxy_config,
            "extra": self.extra,
        }
        return f"Profile({redact_sensitive(values)!r})"


@dataclass(slots=True)
class Group:
    id: str
    name: str | None = None
    remark: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: Mapping[str, Any]) -> "Group":
        group_id = data.get("group_id", data.get("id"))
        if group_id is None:
            raise ValueError("Group response does not contain a group id")
        known = {"group_id", "id", "group_name", "name", "remark"}
        return cls(
            id=str(group_id),
            name=data.get("group_name", data.get("name")),
            remark=data.get("remark"),
            extra={key: value for key, value in data.items() if key not in known},
        )


@dataclass(slots=True)
class BrowserConnection:
    selenium: str | None = None
    playwright_cdp: str | None = None
    debug_port: int | None = None
    webdriver: str | None = None
    marionette_port: int | None = None
    marionette_host: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: Mapping[str, Any], *, base_url: str) -> "BrowserConnection":
        ws_value = data.get("ws")
        ws: Mapping[str, Any] = ws_value if isinstance(ws_value, Mapping) else {}
        debug_port_raw = data.get("debug_port")
        debug_port = int(debug_port_raw) if debug_port_raw not in (None, "") else None
        marionette_raw = data.get("marionette_port")
        marionette_port = int(marionette_raw) if marionette_raw not in (None, "") else None
        selenium = ws.get("selenium") or data.get("selenium")
        playwright = ws.get("puppeteer") or data.get("playwright_cdp")
        api_host = urlsplit(base_url).hostname or "127.0.0.1"
        loopback_hosts = {"127.0.0.1", "localhost", "::1"}
        marionette_host = data.get("marionette_host") or (
            api_host if marionette_port is not None and api_host not in loopback_hosts else None
        )
        if selenium and api_host not in loopback_hosts:
            parsed_selenium = urlsplit(f"//{selenium}")
            if parsed_selenium.hostname in loopback_hosts and parsed_selenium.port:
                selenium = f"{_format_host(api_host)}:{parsed_selenium.port}"
        if playwright and api_host not in loopback_hosts:
            parsed_playwright = urlsplit(str(playwright))
            if parsed_playwright.hostname in loopback_hosts:
                port = f":{parsed_playwright.port}" if parsed_playwright.port else ""
                playwright = urlunsplit(
                    (
                        parsed_playwright.scheme,
                        f"{_format_host(api_host)}{port}",
                        parsed_playwright.path,
                        parsed_playwright.query,
                        parsed_playwright.fragment,
                    )
                )
        if debug_port is not None and not selenium:
            selenium = f"{_format_host(api_host)}:{debug_port}"
        known = {"ws", "debug_port", "webdriver", "selenium", "playwright_cdp", "marionette_port", "marionette_host"}
        return cls(
            selenium=str(selenium) if selenium else None,
            playwright_cdp=str(playwright) if playwright else None,
            debug_port=debug_port,
            webdriver=str(data["webdriver"]) if data.get("webdriver") else None,
            marionette_port=marionette_port,
            marionette_host=str(marionette_host) if marionette_host else None,
            extra={key: value for key, value in data.items() if key not in known},
        )


@dataclass(frozen=True, slots=True)
class ProfileSelector:
    profile_id: str | None = None
    profile_no: str | None = None

    def __post_init__(self) -> None:
        if not self.profile_id and not self.profile_no:
            raise AdsPowerValidationError("profile_id or profile_no is required")

    @property
    def payload(self) -> dict[str, str]:
        if self.profile_id:
            return {"profile_id": str(self.profile_id)}
        return {"profile_no": str(self.profile_no)}


@dataclass(slots=True)
class BrowserStatus:
    status: str
    connection: BrowserConnection | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def active(self) -> bool:
        return self.status.lower() == "active"


@dataclass(slots=True)
class RunningBrowser:
    profile_id: str
    connection: BrowserConnection
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Proxy:
    id: str
    type: str | None = None
    host: str | None = None
    port: str | None = None
    user: str | None = None
    password: str | None = field(default=None, repr=False)
    proxy_url: str | None = None
    remark: str | None = None
    ipchecker: str | None = None
    proxy_partner: str | None = None
    profile_count: int | None = None
    related_profile_no: list[str] = field(default_factory=list)
    proxy_tags: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: Mapping[str, Any]) -> "Proxy":
        proxy_id = data.get("proxy_id", data.get("id"))
        if proxy_id in (None, ""):
            raise ValueError("Proxy response does not contain a proxy id")
        known = {
            "proxy_id", "id", "proxy_type", "type", "proxy_host", "host", "proxy_port", "port",
            "proxy_user", "user", "proxy_password", "password", "proxy_url", "remark", "ipchecker",
            "proxy_partner", "profile_count", "related_profile_no", "proxy_tags",
        }
        count = data.get("profile_count")
        return cls(
            id=str(proxy_id),
            type=data.get("proxy_type", data.get("type")),
            host=data.get("proxy_host", data.get("host")),
            port=str(data["proxy_port"] if data.get("proxy_port") is not None else data["port"]) if data.get("proxy_port", data.get("port")) is not None else None,
            user=data.get("proxy_user", data.get("user")),
            password=data.get("proxy_password", data.get("password")),
            proxy_url=data.get("proxy_url"),
            remark=data.get("remark"),
            ipchecker=data.get("ipchecker"),
            proxy_partner=data.get("proxy_partner"),
            profile_count=int(count) if count is not None else None,
            related_profile_no=[str(item) for item in data.get("related_profile_no", []) or []],
            proxy_tags=list(data.get("proxy_tags", []) or []),
            extra={key: value for key, value in data.items() if key not in known},
        )

    def __repr__(self) -> str:
        values = {key: value for key, value in self.__dict__.items()} if hasattr(self, "__dict__") else {
            "id": self.id, "type": self.type, "host": self.host, "port": self.port, "user": self.user,
            "password": self.password, "proxy_url": self.proxy_url, "remark": self.remark,
            "ipchecker": self.ipchecker, "proxy_partner": self.proxy_partner, "profile_count": self.profile_count,
            "related_profile_no": self.related_profile_no, "proxy_tags": self.proxy_tags, "extra": self.extra,
        }
        return f"Proxy({redact_sensitive(values)!r})"


@dataclass(slots=True)
class Category:
    id: str
    name: str | None = None
    remark: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: Mapping[str, Any]) -> "Category":
        category_id = data.get("category_id", data.get("id"))
        if category_id is None:
            raise ValueError("Category response does not contain a category id")
        known = {"category_id", "id", "category_name", "name", "remark"}
        return cls(
            id=str(category_id),
            name=data.get("category_name", data.get("name")),
            remark=data.get("remark"),
            extra={key: value for key, value in data.items() if key not in known},
        )

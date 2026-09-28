from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

from .exceptions import AdsPowerResponseError, AdsPowerValidationError
from .security import redact_sensitive


def _format_host(host: str) -> str:
    """Format a host for an endpoint authority, including IPv6 literals."""
    if ":" in host and not host.startswith("["):
        return f"[{host}]"
    return host


def _first_present(data: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return None


def _optional_int(value: Any, *, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise AdsPowerResponseError(f"AdsPower returned an invalid {field_name!r} value") from exc


class ProxySoftware(str, Enum):
    """Known AdsPower proxy software/provider identifiers."""

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
    """Helpers for serializing AdsPower screen-resolution values."""

    @staticmethod
    def fixed(width: int, height: int) -> str:
        if width <= 0 or height <= 0:
            raise ValueError("Screen dimensions must be positive")
        return f"{width}_{height}"


@dataclass(slots=True)
class Profile:
    """Persistent AdsPower browser-profile data returned by the Local API."""

    id: str
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
    user_proxy_config: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: Mapping[str, Any]) -> "Profile":
        profile_id = _first_present(data, "profile_id", "user_id", "id")
        if profile_id in (None, ""):
            raise AdsPowerResponseError("Profile response does not contain a profile id")

        proxy_config = data.get("user_proxy_config")
        if proxy_config is not None and not isinstance(proxy_config, Mapping):
            raise AdsPowerResponseError("Profile response contains a malformed user_proxy_config")

        known = {
            "profile_id",
            "user_id",
            "id",
            "profile_no",
            "serial_number",
            "name",
            "group_id",
            "user_proxy_config",
            "group_name",
            "platform",
            "domain_name",
            "username",
            "remark",
            "category_id",
            "created_time",
            "last_open_time",
        }
        profile_no = _first_present(data, "profile_no", "serial_number")
        return cls(
            id=str(profile_id),
            profile_no=str(profile_no) if profile_no is not None else None,
            name=data.get("name"),
            group_id=str(data["group_id"]) if data.get("group_id") is not None else None,
            group_name=data.get("group_name"),
            platform=_first_present(data, "platform", "domain_name"),
            username=data.get("username"),
            remark=data.get("remark"),
            category_id=str(data["category_id"]) if data.get("category_id") is not None else None,
            created_time=str(data["created_time"]) if data.get("created_time") is not None else None,
            last_open_time=str(data["last_open_time"]) if data.get("last_open_time") is not None else None,
            user_proxy_config=dict(proxy_config) if isinstance(proxy_config, Mapping) else None,
            extra={key: value for key, value in data.items() if key not in known},
        )

    @property
    def number(self) -> str | None:
        """Compatibility alias for the pre-freeze `profile_no` field name."""
        return self.profile_no

    def __repr__(self) -> str:
        values = {
            "id": self.id,
            "profile_no": self.profile_no,
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
    """AdsPower profile group."""

    id: str
    name: str | None = None
    remark: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: Mapping[str, Any]) -> "Group":
        group_id = _first_present(data, "group_id", "id")
        if group_id in (None, ""):
            raise AdsPowerResponseError("Group response does not contain a group id")
        known = {"group_id", "id", "group_name", "name", "remark"}
        return cls(
            id=str(group_id),
            name=_first_present(data, "group_name", "name"),
            remark=data.get("remark"),
            extra={key: value for key, value in data.items() if key not in known},
        )


@dataclass(slots=True)
class BrowserConnection:
    """Connection information for a browser process started by AdsPower."""

    selenium_debugger_address: str | None = None
    playwright_cdp_url: str | None = None
    debug_port: int | None = None
    webdriver: str | None = None
    marionette_port: int | None = None
    marionette_host: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(
        cls,
        data: Mapping[str, Any],
        *,
        base_url: str,
        browser_host: str | None = None,
        endpoint_policy: str = "rewrite_loopback_to_api_host",
    ) -> "BrowserConnection":
        ws_value = data.get("ws")
        if ws_value is not None and not isinstance(ws_value, Mapping):
            raise AdsPowerResponseError("Browser response contains a malformed ws object")
        ws: Mapping[str, Any] = ws_value if isinstance(ws_value, Mapping) else {}

        debug_port = _optional_int(data.get("debug_port"), field_name="debug_port")
        marionette_port = _optional_int(data.get("marionette_port"), field_name="marionette_port")
        selenium = _first_present(ws, "selenium") or data.get("selenium")
        playwright = _first_present(ws, "puppeteer") or data.get("playwright_cdp")

        api_host = urlsplit(base_url).hostname or "127.0.0.1"
        target_host = browser_host or api_host
        loopback_hosts = {"127.0.0.1", "localhost", "::1"}
        rewrite_loopback = endpoint_policy == "rewrite_loopback_to_api_host"

        marionette_host = data.get("marionette_host")
        if marionette_host is None and marionette_port is not None and target_host not in loopback_hosts:
            marionette_host = target_host

        if selenium and rewrite_loopback and target_host not in loopback_hosts:
            parsed_selenium = urlsplit(f"//{selenium}")
            if parsed_selenium.hostname in loopback_hosts and parsed_selenium.port:
                selenium = f"{_format_host(target_host)}:{parsed_selenium.port}"

        if playwright and rewrite_loopback and target_host not in loopback_hosts:
            parsed_playwright = urlsplit(str(playwright))
            if parsed_playwright.hostname in loopback_hosts:
                port = f":{parsed_playwright.port}" if parsed_playwright.port else ""
                playwright = urlunsplit(
                    (
                        parsed_playwright.scheme,
                        f"{_format_host(target_host)}{port}",
                        parsed_playwright.path,
                        parsed_playwright.query,
                        parsed_playwright.fragment,
                    )
                )

        if debug_port is not None and not selenium:
            selenium = f"{_format_host(target_host)}:{debug_port}"

        known = {
            "ws",
            "debug_port",
            "webdriver",
            "selenium",
            "playwright_cdp",
            "marionette_port",
            "marionette_host",
        }
        return cls(
            selenium_debugger_address=str(selenium) if selenium else None,
            playwright_cdp_url=str(playwright) if playwright else None,
            debug_port=debug_port,
            webdriver=str(data["webdriver"]) if data.get("webdriver") else None,
            marionette_port=marionette_port,
            marionette_host=str(marionette_host) if marionette_host else None,
            extra={key: value for key, value in data.items() if key not in known},
        )

    @property
    def selenium(self) -> str | None:
        """Compatibility alias for `selenium_debugger_address`."""
        return self.selenium_debugger_address

    @property
    def playwright_cdp(self) -> str | None:
        """Compatibility alias for `playwright_cdp_url`."""
        return self.playwright_cdp_url


@dataclass(frozen=True, slots=True)
class ProfileSelector:
    """Exactly one profile identifier accepted by browser/profile selector endpoints."""

    profile_id: str | None = None
    profile_no: str | None = None

    def __post_init__(self) -> None:
        if bool(self.profile_id) == bool(self.profile_no):
            raise AdsPowerValidationError("exactly one of profile_id or profile_no is required")

    @property
    def payload(self) -> dict[str, str]:
        if self.profile_id:
            return {"profile_id": str(self.profile_id)}
        return {"profile_no": str(self.profile_no)}


@dataclass(slots=True)
class BrowserStatus:
    """Current AdsPower browser activity state and optional connection details."""

    status: str
    connection: BrowserConnection | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def active(self) -> bool:
        return self.status.lower() == "active"


@dataclass(slots=True)
class RunningBrowser:
    """One active browser returned by the Local API active-browser listing."""

    profile_id: str
    connection: BrowserConnection
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Proxy:
    """Stored AdsPower proxy record."""

    id: str
    proxy_type: str | None = None
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
        proxy_id = _first_present(data, "proxy_id", "id")
        if proxy_id in (None, ""):
            raise AdsPowerResponseError("Proxy response does not contain a proxy id")

        count = data.get("profile_count")
        if count is not None:
            try:
                count = int(count)
            except (TypeError, ValueError) as exc:
                raise AdsPowerResponseError("Proxy response contains an invalid profile_count") from exc

        related = data.get("related_profile_no", []) or []
        tags = data.get("proxy_tags", []) or []
        if not isinstance(related, list) or not isinstance(tags, list):
            raise AdsPowerResponseError("Proxy response contains malformed list fields")
        if not all(isinstance(item, Mapping) for item in tags):
            raise AdsPowerResponseError("Proxy response contains a malformed proxy_tags item")

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
        port = _first_present(data, "proxy_port", "port")
        return cls(
            id=str(proxy_id),
            proxy_type=_first_present(data, "proxy_type", "type"),
            host=_first_present(data, "proxy_host", "host"),
            port=str(port) if port is not None else None,
            user=_first_present(data, "proxy_user", "user"),
            password=_first_present(data, "proxy_password", "password"),
            proxy_url=data.get("proxy_url"),
            remark=data.get("remark"),
            ipchecker=data.get("ipchecker"),
            proxy_partner=data.get("proxy_partner"),
            profile_count=count,
            related_profile_no=[str(item) for item in related],
            proxy_tags=[dict(item) for item in tags],
            extra={key: value for key, value in data.items() if key not in known},
        )

    @property
    def type(self) -> str | None:
        """Compatibility alias for `proxy_type`."""
        return self.proxy_type

    def __repr__(self) -> str:
        values = {
            "id": self.id,
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
        return f"Proxy({redact_sensitive(values)!r})"


@dataclass(slots=True)
class Category:
    """AdsPower browser-profile category."""

    id: str
    name: str | None = None
    remark: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: Mapping[str, Any]) -> "Category":
        category_id = _first_present(data, "category_id", "id")
        if category_id in (None, ""):
            raise AdsPowerResponseError("Category response does not contain a category id")
        known = {"category_id", "id", "category_name", "name", "remark"}
        return cls(
            id=str(category_id),
            name=_first_present(data, "category_name", "name"),
            remark=data.get("remark"),
            extra={key: value for key, value in data.items() if key not in known},
        )

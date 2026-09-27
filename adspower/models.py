from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping
from urllib.parse import urlsplit


class ProxySoftware(str, Enum):
    BRIGHTDATA = "brightdata"
    BRIGHTAUTO = "brightauto"
    OXYLABS_AUTO = "oxylabsauto"
    IPFOXY_AUTO = "ipfoxyauto"
    KOOK_AUTO = "kookauto"
    LUMIPROXY_AUTO = "lumiproxyauto"
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
        }
        number = data.get("profile_no", data.get("serial_number"))
        return cls(
            id=str(profile_id),
            number=str(number) if number is not None else None,
            name=data.get("name"),
            group_id=str(data["group_id"]) if data.get("group_id") is not None else None,
            user_proxy_config=data.get("user_proxy_config"),
            extra={key: value for key, value in data.items() if key not in known},
        )


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
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: Mapping[str, Any], *, base_url: str) -> "BrowserConnection":
        ws = data.get("ws") if isinstance(data.get("ws"), Mapping) else {}
        debug_port_raw = data.get("debug_port")
        debug_port = int(debug_port_raw) if debug_port_raw not in (None, "") else None
        selenium = ws.get("selenium") or data.get("selenium")
        playwright = ws.get("puppeteer") or data.get("playwright_cdp")
        if debug_port is not None and not selenium:
            host = urlsplit(base_url).hostname or "127.0.0.1"
            selenium = f"{host}:{debug_port}"
        known = {"ws", "debug_port", "webdriver", "selenium", "playwright_cdp"}
        return cls(
            selenium=str(selenium) if selenium else None,
            playwright_cdp=str(playwright) if playwright else None,
            debug_port=debug_port,
            webdriver=str(data["webdriver"]) if data.get("webdriver") else None,
            extra={key: value for key, value in data.items() if key not in known},
        )

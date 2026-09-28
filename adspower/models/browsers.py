from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from .._json import JsonValue, collect_extra, first_present, optional_int, optional_string, require_id_string, require_object
from ..errors import AdsPowerProtocolError


@dataclass(frozen=True, slots=True)
class BrowserConnection:
    selenium_debugger_address: str | None = None
    playwright_cdp_url: str | None = None
    debug_port: int | None = None
    webdriver: str | None = None
    marionette_port: int | None = None
    marionette_host: str | None = None
    raw_selenium_debugger_address: str | None = None
    raw_playwright_cdp_url: str | None = None
    extra: Mapping[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BrowserStatus:
    status: str
    connection: BrowserConnection | None = None
    extra: Mapping[str, JsonValue] = field(default_factory=dict)

    @property
    def active(self) -> bool:
        return self.status.lower() == "active"


@dataclass(frozen=True, slots=True)
class RunningBrowser:
    profile_id: str
    connection: BrowserConnection
    extra: Mapping[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CloudBrowserStatus:
    profile_id: str
    status: str
    extra: Mapping[str, JsonValue] = field(default_factory=dict)


def parse_browser_connection(value: object) -> BrowserConnection:
    data = require_object(value, field="browser connection")
    ws_value = data.get("ws")
    ws = require_object(ws_value, field="ws") if ws_value is not None else {}
    selenium = first_present(ws, "selenium") or data.get("selenium")
    playwright = first_present(ws, "puppeteer") or data.get("playwright_cdp")
    selenium_s = optional_string(selenium, field="ws.selenium")
    playwright_s = optional_string(playwright, field="ws.puppeteer")
    debug_port = optional_int(data.get("debug_port"), field="debug_port")
    if selenium_s is None and debug_port is None and playwright_s is None and data.get("marionette_port") is None:
        raise AdsPowerProtocolError("browser start response does not contain a usable connection endpoint")
    known = {"ws", "debug_port", "webdriver", "selenium", "playwright_cdp", "marionette_port", "marionette_host"}
    return BrowserConnection(
        selenium_debugger_address=selenium_s,
        playwright_cdp_url=playwright_s,
        debug_port=debug_port,
        webdriver=optional_string(data.get("webdriver"), field="webdriver"),
        marionette_port=optional_int(data.get("marionette_port"), field="marionette_port"),
        marionette_host=optional_string(data.get("marionette_host"), field="marionette_host"),
        raw_selenium_debugger_address=selenium_s,
        raw_playwright_cdp_url=playwright_s,
        extra=collect_extra(data, known),
    )


def parse_browser_status(value: object) -> BrowserStatus:
    data = require_object(value, field="browser status")
    status = optional_string(data.get("status"), field="status")
    if status is None:
        raise AdsPowerProtocolError("browser status response is missing status")
    connection = None
    if any(key in data for key in ("ws", "debug_port", "selenium", "playwright_cdp", "marionette_port")):
        connection = parse_browser_connection(data)
    return BrowserStatus(status, connection, collect_extra(data, {"status", "ws", "debug_port", "webdriver", "selenium", "playwright_cdp", "marionette_port", "marionette_host"}))


def parse_running_browser(value: object) -> RunningBrowser:
    data = require_object(value, field="running browser")
    profile_id = require_id_string(first_present(data, "profile_id", "user_id", "id"), field="profile_id")
    return RunningBrowser(profile_id, parse_browser_connection(data), collect_extra(data, {"profile_id", "user_id", "id", "ws", "debug_port", "webdriver", "selenium", "playwright_cdp", "marionette_port", "marionette_host"}))


def parse_cloud_browser_status(value: object) -> CloudBrowserStatus:
    data = require_object(value, field="cloud browser status")
    return CloudBrowserStatus(
        require_id_string(first_present(data, "profile_id", "user_id", "id"), field="profile_id"),
        optional_string(data.get("status"), field="status") or "unknown",
        collect_extra(data, {"profile_id", "user_id", "id", "status"}),
    )

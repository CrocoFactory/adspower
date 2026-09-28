from __future__ import annotations

import pytest

from adspower import AdsPowerConfig, BrowserConnection
from adspower.automation.endpoints import remote_chromium_version, resolve_browser_connection
from adspower.errors import AdsPowerConfigurationError, AdsPowerProtocolError


def test_endpoint_resolution_exact_and_remote_rewrite() -> None:
    connection = BrowserConnection(
        selenium_debugger_address="127.0.0.1:9222",
        playwright_cdp_url="ws://127.0.0.1:9222/devtools/browser/id",
        raw_selenium_debugger_address="127.0.0.1:9222",
        raw_playwright_cdp_url="ws://127.0.0.1:9222/devtools/browser/id",
    )
    exact = resolve_browser_connection(
        connection,
        AdsPowerConfig.resolve(
            base_url="http://10.0.0.2:50325",
            browser_endpoint_policy="exact",
        ),
    )
    assert exact.selenium_debugger_address == "127.0.0.1:9222"

    rewritten = resolve_browser_connection(
        connection,
        AdsPowerConfig.resolve(base_url="http://10.0.0.2:50325"),
    )
    assert rewritten.selenium_debugger_address == "10.0.0.2:9222"
    assert rewritten.playwright_cdp_url == "ws://10.0.0.2:9222/devtools/browser/id"


def test_endpoint_resolution_ipv6() -> None:
    connection = BrowserConnection(debug_port=9222)
    resolved = resolve_browser_connection(
        connection,
        AdsPowerConfig.resolve(
            base_url="http://127.0.0.1:50325",
            browser_host="2001:db8::1",
        ),
    )
    assert resolved.selenium_debugger_address == "[2001:db8::1]:9222"


def test_remote_version_probe_is_injectable() -> None:
    calls: list[tuple[str, float]] = []

    def get(url: str, timeout: float) -> object:
        calls.append((url, timeout))
        return {"Browser": "Chrome/141.0.1.2"}

    assert remote_chromium_version("example.test:9222", timeout=0.5, get=get) == "141"
    assert calls == [("http://example.test:9222/json/version", 0.5)]

    with pytest.raises(AdsPowerProtocolError):
        remote_chromium_version("example.test:9222", get=lambda *_: {"Browser": "Firefox/1"})
    with pytest.raises(AdsPowerConfigurationError):
        remote_chromium_version("bad-address", get=get)

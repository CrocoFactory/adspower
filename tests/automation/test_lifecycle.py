from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from adspower import BrowserConnection
from adspower.automation.playwright import AsyncPlaywrightAdapter, PlaywrightAdapter
from adspower.automation.selenium import SeleniumAdapter
from adspower.errors import AdsPowerProtocolError, AdsPowerValidationError


class FakeBrowser:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeAsyncBrowser:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def install_sync_playwright(monkeypatch: pytest.MonkeyPatch, browser: FakeBrowser) -> list[str]:
    events: list[str] = []

    class Runtime:
        chromium = types.SimpleNamespace(
            connect_over_cdp=lambda endpoint, **kwargs: browser
        )

        def stop(self) -> None:
            events.append("runtime-stop")

    class Manager:
        def start(self) -> Runtime:
            events.append("runtime-start")
            return Runtime()

    module = types.ModuleType("playwright.sync_api")
    module.sync_playwright = lambda: Manager()  # type: ignore[attr-defined]
    package = types.ModuleType("playwright")
    monkeypatch.setitem(sys.modules, "playwright", package)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", module)
    return events


def test_sync_playwright_adapter_owns_only_attachment(monkeypatch: pytest.MonkeyPatch) -> None:
    browser = FakeBrowser()
    events = install_sync_playwright(monkeypatch, browser)
    adapter = PlaywrightAdapter(
        BrowserConnection(playwright_cdp_url="ws://localhost/devtools/browser/id")
    )
    with adapter as connected:
        assert connected is browser
    assert browser.closed
    assert events == ["runtime-start", "runtime-stop"]


def test_playwright_requires_endpoint_and_rejects_duplicate_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_sync_playwright(monkeypatch, FakeBrowser())
    with pytest.raises(AdsPowerProtocolError):
        with PlaywrightAdapter(BrowserConnection()):
            pass
    with pytest.raises(AdsPowerValidationError):
        PlaywrightAdapter(
            BrowserConnection(playwright_cdp_url="ws://x"),
            timeout=1,
            connect_kwargs={"timeout": 2},
        )


@pytest.mark.asyncio
async def test_async_playwright_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    browser = FakeAsyncBrowser()
    events: list[str] = []

    class Chromium:
        async def connect_over_cdp(self, endpoint: str, **kwargs: Any) -> FakeAsyncBrowser:
            return browser

    class Runtime:
        chromium = Chromium()

        async def stop(self) -> None:
            events.append("runtime-stop")

    class Manager:
        async def start(self) -> Runtime:
            events.append("runtime-start")
            return Runtime()

    module = types.ModuleType("playwright.async_api")
    module.async_playwright = lambda: Manager()  # type: ignore[attr-defined]
    package = types.ModuleType("playwright")
    monkeypatch.setitem(sys.modules, "playwright", package)
    monkeypatch.setitem(sys.modules, "playwright.async_api", module)

    adapter = AsyncPlaywrightAdapter(
        BrowserConnection(playwright_cdp_url="ws://localhost/devtools/browser/id")
    )
    async with adapter as connected:
        assert connected is browser
    assert browser.closed
    assert events == ["runtime-start", "runtime-stop"]


def test_selenium_validates_options_before_import() -> None:
    adapter = SeleniumAdapter(
        BrowserConnection(selenium_debugger_address="localhost:9222"),
        service=object(),
        service_kwargs={"x": 1},
    )
    with pytest.raises(AdsPowerValidationError):
        adapter.__enter__()

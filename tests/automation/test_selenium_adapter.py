from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from adspower import BrowserConnection
from adspower.automation import selenium as selenium_module
from adspower.automation.selenium import SeleniumAdapter
from adspower.errors import AdsPowerProtocolError, AdsPowerValidationError


class FakeOptions:
    def __init__(self) -> None:
        self._experimental_options: dict[str, object] = {}
        self.page_load_strategy: str | None = None
        self.browser_version: str | None = None

    def add_experimental_option(self, name: str, value: object) -> None:
        self._experimental_options[name] = value


class FakeService:
    instances: list["FakeService"] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.instances.append(self)


class FakeDriver:
    instances: list["FakeDriver"] = []

    def __init__(self, *, service: object, options: object, **kwargs: Any) -> None:
        self.service = service
        self.options = options
        self.kwargs = kwargs
        self.quit_called = False
        self.instances.append(self)

    def quit(self) -> None:
        self.quit_called = True


def install_selenium_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    modules = {
        "selenium.webdriver.chrome.options": ("Options", FakeOptions),
        "selenium.webdriver.chrome.service": ("Service", FakeService),
        "selenium.webdriver.chrome.webdriver": ("WebDriver", FakeDriver),
        "selenium.webdriver.firefox.options": ("Options", FakeOptions),
        "selenium.webdriver.firefox.service": ("Service", FakeService),
        "selenium.webdriver.firefox.webdriver": ("WebDriver", FakeDriver),
    }
    for name, (attribute, value) in modules.items():
        module = types.ModuleType(name)
        setattr(module, attribute, value)
        monkeypatch.setitem(sys.modules, name, module)


def test_chromium_adapter_builds_options_and_quits(monkeypatch: pytest.MonkeyPatch) -> None:
    install_selenium_modules(monkeypatch)
    FakeDriver.instances.clear()
    options = FakeOptions()

    adapter = SeleniumAdapter(
        BrowserConnection(selenium_debugger_address="localhost:9222"),
        options=options,
        page_load_strategy="eager",
        webdriver_kwargs={"keep_alive": False},
    )
    with adapter as driver:
        assert driver is FakeDriver.instances[-1]
        assert options.page_load_strategy == "eager"
        assert options._experimental_options["debuggerAddress"] == "localhost:9222"
        assert driver.kwargs == {"keep_alive": False}

    assert FakeDriver.instances[-1].quit_called


def test_chromium_adapter_uses_local_webdriver_path(monkeypatch: pytest.MonkeyPatch) -> None:
    install_selenium_modules(monkeypatch)
    FakeService.instances.clear()
    monkeypatch.setattr(selenium_module.os.path, "isfile", lambda _: True)

    with SeleniumAdapter(
        BrowserConnection(
            selenium_debugger_address="127.0.0.1:9222",
            webdriver="/tmp/chromedriver",
        )
    ):
        pass

    assert FakeService.instances[-1].kwargs["executable_path"] == "/tmp/chromedriver"


def test_chromium_remote_probe_sets_browser_version(monkeypatch: pytest.MonkeyPatch) -> None:
    install_selenium_modules(monkeypatch)
    calls: list[tuple[str, float]] = []
    monkeypatch.setattr(
        selenium_module,
        "remote_chromium_version",
        lambda address, timeout: calls.append((address, timeout)) or "141",
    )
    options = FakeOptions()

    with SeleniumAdapter(
        BrowserConnection(selenium_debugger_address="10.0.0.2:9222"),
        options=options,
        probe_timeout=0.25,
    ):
        pass

    assert options.browser_version == "141"
    assert calls == [("10.0.0.2:9222", 0.25)]


def test_firefox_adapter_builds_marionette_service_args(monkeypatch: pytest.MonkeyPatch) -> None:
    install_selenium_modules(monkeypatch)
    FakeService.instances.clear()

    with SeleniumAdapter(
        BrowserConnection(marionette_port=2828, marionette_host="10.0.0.3"),
        browser="firefox",
        service_kwargs={"service_args": ["--existing"]},
    ):
        pass

    args = FakeService.instances[-1].kwargs["service_args"]
    assert args == [
        "--existing",
        "--marionette-port",
        "2828",
        "--connect-existing",
        "--marionette-host",
        "10.0.0.3",
    ]


def test_selenium_endpoint_and_option_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    install_selenium_modules(monkeypatch)

    with pytest.raises(AdsPowerProtocolError):
        SeleniumAdapter(BrowserConnection()).__enter__()

    with pytest.raises(AdsPowerProtocolError):
        SeleniumAdapter(BrowserConnection(), browser="firefox").__enter__()

    options = FakeOptions()
    options.add_experimental_option("debuggerAddress", "other:9222")
    with pytest.raises(AdsPowerValidationError):
        SeleniumAdapter(
            BrowserConnection(selenium_debugger_address="localhost:9222"),
            options=options,
        ).__enter__()

    with pytest.raises(AdsPowerValidationError):
        SeleniumAdapter(
            BrowserConnection(selenium_debugger_address="localhost:9222"),
            webdriver_kwargs={"service": object()},
        ).__enter__()


def test_close_error_is_preserved_or_raised() -> None:
    class BadDriver:
        def quit(self) -> None:
            raise RuntimeError("quit failed")

    adapter = SeleniumAdapter(BrowserConnection(selenium_debugger_address="localhost:9222"))
    adapter.driver = BadDriver()
    with pytest.raises(RuntimeError, match="quit failed"):
        adapter.close()

    adapter2 = SeleniumAdapter(BrowserConnection(selenium_debugger_address="localhost:9222"))
    adapter2.driver = BadDriver()
    adapter2.close(preserve_error=True)
    adapter2.close()

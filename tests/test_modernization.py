from __future__ import annotations

import json
import sys
import types

import httpx
import pytest

from adspower import AdsPowerClient, AsyncAdsPowerClient
from adspower.automation import _playwright_connect_kwargs
from adspower.exceptions import AdsPowerValidationError
from adspower.models import BrowserConnection, Profile, Proxy


def response(payload: object, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload)


def test_profile_proxy_defaults_are_semantic() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return response({"code": 0, "data": {"profile_id": "p"}})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        client.profiles.create(proxyid="saved")
        client.profiles.create(user_proxy_config={"proxy_type": "http"}, fingerprint_config=None)
        client.profiles.create()

    first, second, third = [json.loads(request.content) for request in requests]
    assert first["proxyid"] == "saved"
    assert "user_proxy_config" not in first
    assert second["user_proxy_config"] == {"proxy_type": "http"}
    assert third["user_proxy_config"] == {"proxy_soft": "no_proxy"}
    assert second["fingerprint_config"]["automatic_timezone"] == "1"


def test_profile_operations_and_cookie_normalization() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path.endswith("cookies"):
            return response({"code": 0, "data": {"cookies": '[{"name":"sid","value":"secret"}]'}})
        if request.url.path.endswith("local-active"):
            return response({"code": 0, "data": [{"profile_id": "p", "debug_port": "9222"}]})
        if request.url.path.endswith("active"):
            return response({"code": 0, "data": {"status": "Active", "debug_port": "9222"}})
        return response({"code": 0, "data": {"group_name": "Share"}})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        client.profiles.delete_many(["p1", "p2"])
        client.profiles.move(["p1"], "g")
        client.profiles.delete_cache(["p1"], ["indexeddb"])
        assert client.profiles.cookies(profile_no="7")[0]["name"] == "sid"
        assert client.profiles.share(["p1"], "user@example.com")["group_name"] == "Share"
        assert client.browsers.status(profile_no="7").active
        assert client.browsers.list_active()[0].profile_id == "p"

    assert paths == [
        "/api/v2/browser-profile/delete",
        "/api/v1/user/regroup",
        "/api/v2/browser-profile/delete-cache",
        "/api/v2/browser-profile/cookies",
        "/api/v2/browser-profile/share",
        "/api/v2/browser-profile/active",
        "/api/v1/browser/local-active",
    ]


def test_raw_request_is_relative_and_can_preserve_envelope() -> None:
    with AdsPowerClient(transport=httpx.MockTransport(lambda _: response({"code": 0, "data": {"future": 1}, "msg": "ok"}))) as client:
        assert client.request("POST", "/api/v2/future", json=[1], unwrap=False)["msg"] == "ok"
        with pytest.raises(ValueError):
            client.request("GET", "https://evil.example/steal")
        with pytest.raises(ValueError):
            client.request("GET", "api/v2/relative")


def test_models_redact_credentials_and_cookie_values() -> None:
    profile = Profile.from_api({"profile_id": "p", "password": "real-password", "fakey": "2fa-secret", "user_proxy_config": {"proxy_password": "proxy-password"}, "cookie": "cookie-value"})
    proxy = Proxy.from_api({"proxy_id": "x", "proxy_password": "proxy-password"})
    assert "real-password" not in repr(profile)
    assert "2fa-secret" not in repr(profile)
    assert "proxy-password" not in repr(profile)
    assert "cookie-value" not in repr(profile)
    assert "proxy-password" not in repr(proxy)


def test_validation_and_playwright_future_options() -> None:
    with pytest.raises(AdsPowerValidationError):
        from adspower.api import _ids
        _ids([], name="ids", maximum=100)
    assert _playwright_connect_kwargs(timeout=1, no_defaults=True, connect_kwargs={"future": 2}) == {"timeout": 1, "no_defaults": True, "future": 2}
    with pytest.raises(ValueError):
        _playwright_connect_kwargs(timeout=1, connect_kwargs={"timeout": 2})


def _install_fake_selenium(monkeypatch: pytest.MonkeyPatch) -> tuple[type, type, type]:
    class Options:
        def __init__(self) -> None:
            self._experimental_options: dict[str, object] = {}

        def add_experimental_option(self, key: str, value: object) -> None:
            self._experimental_options[key] = value

    class Service:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    class Driver:
        instances: list["Driver"] = []

        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs
            self.quit_called = False
            self.maximized = False
            self.__class__.instances.append(self)

        def maximize_window(self) -> None:
            self.maximized = True

        def quit(self) -> None:
            self.quit_called = True

    selenium = types.ModuleType("selenium")
    webdriver = types.ModuleType("selenium.webdriver")
    chrome = types.ModuleType("selenium.webdriver.chrome")
    chrome_options = types.ModuleType("selenium.webdriver.chrome.options")
    chrome_service = types.ModuleType("selenium.webdriver.chrome.service")
    chrome_driver = types.ModuleType("selenium.webdriver.chrome.webdriver")
    firefox = types.ModuleType("selenium.webdriver.firefox")
    firefox_options = types.ModuleType("selenium.webdriver.firefox.options")
    firefox_service = types.ModuleType("selenium.webdriver.firefox.service")
    firefox_driver = types.ModuleType("selenium.webdriver.firefox.webdriver")
    chrome_options.Options = Options
    chrome_service.Service = Service
    chrome_driver.WebDriver = Driver
    firefox_options.Options = Options
    firefox_service.Service = Service
    firefox_driver.WebDriver = Driver
    for module in (selenium, webdriver, chrome, chrome_options, chrome_service, chrome_driver, firefox, firefox_options, firefox_service, firefox_driver):
        monkeypatch.setitem(sys.modules, module.__name__, module)
    return Options, Service, Driver


def test_selenium_configuration_and_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    _, service_type, driver_type = _install_fake_selenium(monkeypatch)
    connection = BrowserConnection(selenium="127.0.0.1:9222", webdriver="/not-on-this-machine")
    stopped: list[bool] = []
    from adspower.automation import SeleniumSession

    service = service_type(port=9515)
    session = SeleniumSession(connection, stop=lambda: stopped.append(True), service=service, start_maximized=True, webdriver_kwargs={"keep_alive": False})
    driver = session.__enter__()
    assert driver.kwargs["service"] is service
    assert driver.kwargs["options"]._experimental_options["debuggerAddress"] == "127.0.0.1:9222"
    assert driver.maximized
    session.close()
    session.close()
    assert driver.quit_called and stopped == [True]
    assert driver_type.instances


def test_firefox_selenium_uses_marionette_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    _, service_type, _ = _install_fake_selenium(monkeypatch)
    from adspower.automation import SeleniumSession

    connection = BrowserConnection(marionette_port=2828, webdriver="/missing/geckodriver")
    session = SeleniumSession(connection, stop=lambda: None, browser="firefox", service_kwargs={"service_args": ["--verbose"]})
    driver = session.__enter__()
    args = driver.kwargs["service"].kwargs["service_args"]
    assert args == ["--verbose", "--marionette-port", "2828", "--connect-existing"]
    session.close()
    assert service_type


def test_playwright_sync_and_async_connection_options(monkeypatch: pytest.MonkeyPatch) -> None:
    class Browser:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class Runtime:
        def __init__(self) -> None:
            self.chromium = self
            self.kwargs: dict[str, object] = {}
            self.browser = Browser()
            self.stopped = False

        def connect_over_cdp(self, endpoint: str, **kwargs: object) -> Browser:
            self.endpoint, self.kwargs = endpoint, kwargs
            return self.browser

        def stop(self) -> None:
            self.stopped = True

    runtime = Runtime()
    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = lambda: types.SimpleNamespace(start=lambda: runtime)
    playwright = types.ModuleType("playwright")
    async_api = types.ModuleType("playwright.async_api")

    class AsyncRuntime:
        def __init__(self) -> None:
            self.chromium = self
            self.browser = types.SimpleNamespace(close=self._close)
            self.kwargs: dict[str, object] = {}
            self.stopped = False

        async def start(self) -> "AsyncRuntime":
            return self

        async def connect_over_cdp(self, endpoint: str, **kwargs: object) -> object:
            self.endpoint, self.kwargs = endpoint, kwargs
            return self.browser

        async def _close(self) -> None:
            self.closed = True

        async def stop(self) -> None:
            self.stopped = True

    async_runtime = AsyncRuntime()
    async_api.async_playwright = lambda: async_runtime
    for module in (playwright, sync_api, async_api):
        monkeypatch.setitem(sys.modules, module.__name__, module)

    from adspower.automation import AsyncPlaywrightSession, PlaywrightSession

    connection = BrowserConnection(playwright_cdp="ws://exact")
    stopped: list[bool] = []
    session = PlaywrightSession(connection, stop=lambda: stopped.append(True), timeout=100, connect_kwargs={"future": 1})
    assert session.__enter__() is runtime.browser
    assert runtime.endpoint == "ws://exact" and runtime.kwargs == {"timeout": 100, "future": 1}
    session.close()
    assert stopped == [True]

    async def check_async() -> None:
        async_session = AsyncPlaywrightSession(connection, stop=lambda: _async_mark(stopped))
        assert await async_session.__aenter__() is async_runtime.browser
        await async_session.close()

    import asyncio
    asyncio.run(check_async())


async def _async_mark(values: list[bool]) -> None:
    values.append(True)


def test_sync_resource_crud_and_paginated_name_search() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path.endswith("browser-profile/list"):
            page = json.loads(request.content).get("page", 1)
            data = [{"profile_id": "p", "name": "needle"}] if page == 1 else []
            return response({"code": 0, "data": {"list": data}})
        if path.endswith("proxy-list/create"):
            return response({"code": 0, "data": {"proxy_ids": ["px1", "px2"]}})
        if path.endswith("proxy-list/list"):
            return response({"code": 0, "data": {"list": [{"proxy_id": "px1", "proxy_type": "http"}]}})
        if path.endswith("category/list"):
            return response({"code": 0, "data": {"list": [{"category_id": "c1"}]}})
        if path.endswith("browser-profile/update"):
            return response({"code": 0, "data": {}})
        return response({"code": 0, "data": {"profile_id": "p"}})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        assert client.profiles.find_by_name("needle", page_size=1).id == "p"
        assert client.profiles.update("p", refresh=True).id == "p"
        assert client.proxies.create(type="http", host="127.0.0.1", port=8080) == ["px1", "px2"]
        client.proxies.update("px1", remark="updated")
        client.proxies.delete("px1")
        client.proxies.delete_many(["px1", "px2"])
        assert client.proxies.list(proxy_ids="px1")[0].id == "px1"
        assert client.categories.list()[0].id == "c1"
        with pytest.raises(AdsPowerValidationError):
            client.groups.list(page_size=2001)
        with pytest.raises(AdsPowerValidationError):
            client.proxies.list(page_size=201)
        with pytest.raises(AdsPowerValidationError):
            client.categories.list(page_size=101)
    assert any(request.url.path.endswith("proxy-list/create") for request in requests)


@pytest.mark.asyncio
async def test_async_profile_operations_and_validation() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("browser-profile/list"):
            page = json.loads(request.content).get("page", 1)
            data = [{"profile_id": "p", "name": "needle"}] if page == 1 else []
            return response({"code": 0, "data": {"list": data}})
        if path.endswith("browser-profile/update"):
            return response({"code": 0, "data": {}})
        return response({"code": 0, "data": {}})

    async with AsyncAdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        assert (await client.profiles.find_by_name("needle", page_size=1)).id == "p"
        assert (await client.profiles.update("p", refresh=True)).id == "p"
        with pytest.raises(AdsPowerValidationError):
            await client.profiles.list(page_size=101)


@pytest.mark.asyncio
async def test_async_resource_parity() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("proxy-list/list"):
            return response({"code": 0, "data": {"list": [{"proxy_id": "p", "proxy_port": "8000"}]}})
        return response({"code": 0, "data": {"list": [{"category_id": "c", "name": "team"}]}})

    async with AsyncAdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        assert (await client.proxies.list())[0].id == "p"
        assert (await client.categories.list())[0].id == "c"

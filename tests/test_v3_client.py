from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from adspower import AdsPowerClient, AsyncAdsPowerClient, ScreenResolution
from adspower.automation import AsyncPlaywrightSession, PlaywrightSession, SeleniumSession
from adspower.config import DEFAULT_BASE_URL, ClientConfig
from adspower.exceptions import (
    AdsPowerAPIError,
    AdsPowerConnectionError,
    AdsPowerTimeoutError,
    AuthenticationError,
    ProfileNotFoundError,
    RateLimitError,
)
from adspower.models import BrowserConnection, Profile
from adspower.rate_limit import AsyncRateLimiter, RateLimit, SyncRateLimiter


def response(payload: object, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload)


def test_config_precedence_and_redaction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADSPOWER_BASE_URL", "http://docker:50325/")
    monkeypatch.setenv("ADSPOWER_API_KEY", "env-secret")
    env = ClientConfig.resolve()
    explicit = ClientConfig.resolve(base_url="http://remote:1234/", api_key="explicit")
    monkeypatch.delenv("ADSPOWER_BASE_URL")
    default = ClientConfig.resolve(api_key="")

    assert env.base_url == "http://docker:50325"
    assert env.headers == {"Authorization": "Bearer env-secret"}
    assert explicit.base_url == "http://remote:1234"
    assert default.base_url == DEFAULT_BASE_URL
    assert "env-secret" not in repr(env)
    assert "explicit" not in repr(AdsPowerClient(transport=httpx.MockTransport(lambda _: response({"code": 0})), api_key="explicit"))


def test_profile_parser_is_forward_compatible() -> None:
    profile = Profile.from_api(
        {
            "profile_id": "p-1",
            "profile_no": 12,
            "name": "future",
            "user_proxy_config": {"proxy_soft": "future-provider"},
            "future_nested_object": {"x": 1},
        }
    )
    assert profile.id == "p-1"
    assert profile.number == "12"
    assert profile.user_proxy_config == {"proxy_soft": "future-provider"}
    assert profile.extra["future_nested_object"] == {"x": 1}


def test_sync_v2_contract_auth_and_no_preflight() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return response({"code": 0, "data": {"profile_id": "abc", "profile_no": "7", "future": True}})

    with AdsPowerClient(
        base_url="http://remote.internal:50325/",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    ) as client:
        profile = client.profiles.create(
            name="test",
            group_id="0",
            fingerprint_config={"screen_resolution": ScreenResolution.fixed(1920, 1080)},
            user_proxy_config={"proxy_soft": "new-provider"},
        )

    assert profile.id == "abc"
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url.path == "/api/v2/browser-profile/create"
    assert request.headers["Authorization"] == "Bearer secret"
    body = json.loads(request.content)
    assert body["fingerprint_config"]["screen_resolution"] == "1920_1080"
    assert body["user_proxy_config"]["proxy_soft"] == "new-provider"


def test_profile_crud_and_v1_namespace() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path.endswith("/list"):
            return response({"code": 0, "data": {"list": [{"profile_id": "p1"}]}})
        if request.url.path.endswith("/create") and "/v1/" in request.url.path:
            return response({"code": 0, "data": {"id": "legacy"}})
        return response({"code": 0, "data": {}})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        assert client.profiles.get("p1").id == "p1"
        client.profiles.update("p1", name="updated")
        client.profiles.delete("p1")
        assert client.v1.profiles.create(name="old").id == "legacy"

    assert paths == [
        "/api/v2/browser-profile/list",
        "/api/v2/browser-profile/update",
        "/api/v2/browser-profile/delete",
        "/api/v1/user/create",
    ]


def test_profile_not_found() -> None:
    transport = httpx.MockTransport(lambda _: response({"code": 0, "data": {"list": []}}))
    with AdsPowerClient(transport=transport) as client:
        with pytest.raises(ProfileNotFoundError):
            client.profiles.get("missing")


def test_browser_start_uses_returned_endpoints_and_headless_contract() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/start"):
            return response(
                {
                    "code": 0,
                    "data": {
                        "ws": {
                            "selenium": "remote.internal:44001",
                            "puppeteer": "ws://remote.internal:44001/devtools/browser/exact",
                        },
                        "debug_port": "44001",
                        "webdriver": "/opt/adspower/chromedriver",
                    },
                }
            )
        return response({"code": 0, "data": {}})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        session = client.browsers.start("p1", headless=False)
        assert session.connection.playwright_cdp.endswith("/exact")
        assert session.connection.selenium == "remote.internal:44001"
        session.stop()
        session.stop()

    assert json.loads(requests[0].content) == {"profile_id": "p1", "headless": "0"}
    assert [request.url.path for request in requests].count("/api/v2/browser-profile/stop") == 1


@pytest.mark.parametrize(
    ("status", "payload", "error"),
    [
        (401, {"error": "no"}, AuthenticationError),
        (429, {"error": "slow"}, RateLimitError),
        (200, {"code": -1, "msg": "Too many requests"}, RateLimitError),
    ],
)
def test_error_mapping(status: int, payload: dict[str, object], error: type[Exception]) -> None:
    transport = httpx.MockTransport(lambda _: response(payload, status))
    with AdsPowerClient(transport=transport) as client:
        with pytest.raises(error):
            client.health.check()


@pytest.mark.asyncio
async def test_async_parity_and_exact_contract() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return response({"code": "0", "data": {"list": [{"user_id": "async", "new": 1}]}})

    async with AsyncAdsPowerClient(
        api_key="async-secret",
        transport=httpx.MockTransport(handler),
    ) as client:
        profiles = await client.profiles.list(name="test")

    assert profiles[0].id == "async"
    assert profiles[0].extra["new"] == 1
    assert requests[0].headers["Authorization"] == "Bearer async-secret"
    assert requests[0].url.path == "/api/v2/browser-profile/list"


def test_sync_limiter_with_fake_clock() -> None:
    now = [0.0]
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    limiter = SyncRateLimiter(RateLimit(2, 1.0), clock=lambda: now[0], sleep=sleep)
    limiter.acquire()
    limiter.acquire()
    limiter.acquire()
    assert sleeps == [1.0]


@pytest.mark.asyncio
async def test_async_limiter_serializes_concurrent_callers() -> None:
    now = [0.0]
    sleeps: list[float] = []

    async def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    limiter = AsyncRateLimiter(RateLimit(1, 1.0), clock=lambda: now[0], sleep=sleep)
    await asyncio.gather(limiter.acquire(), limiter.acquire(), limiter.acquire())
    assert sleeps == [1.0, 1.0]


def test_browser_connection_remote_fallback() -> None:
    connection = BrowserConnection.from_api({"debug_port": "9222"}, base_url="http://docker-host:50325")
    assert connection.selenium == "docker-host:9222"


def test_groups_and_explicit_health_contracts() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path.endswith("/create"):
            return response({"code": 0, "data": {"group_id": "2", "group_name": "team"}})
        if request.url.path.endswith("/list"):
            return response({"code": 0, "data": {"list": [{"group_id": "2", "group_name": "team"}]}})
        return response({"code": 0, "data": {"status": "ok"}})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        assert client.groups.create("team").id == "2"
        assert client.groups.list(name="team")[0].name == "team"
        assert client.groups.update("2", name="renamed").name == "renamed"
        assert client.health.check() == {"status": "ok"}

    assert paths == ["/api/v1/group/create", "/api/v1/group/list", "/api/v1/group/update", "/status"]


@pytest.mark.asyncio
async def test_async_crud_browser_groups_health_and_v1() -> None:
    paths: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        path = request.url.path
        if path.endswith("browser-profile/create"):
            return response({"code": 0, "data": {"profile_id": "p1"}})
        if path.endswith("browser-profile/update"):
            return response({"code": 0, "data": {"profile_id": "p1", "name": "new"}})
        if path.endswith("browser-profile/start"):
            return response({"code": 0, "data": {"ws": {"puppeteer": "ws://exact"}}})
        if path.endswith("group/create"):
            return response({"code": 0, "data": {"group_id": "g1", "group_name": "g"}})
        if path.endswith("group/list"):
            return response({"code": 0, "data": {"list": [{"group_id": "g1"}]}})
        if path.endswith("user/create"):
            return response({"code": 0, "data": {"id": "old"}})
        if path.endswith("user/list"):
            return response({"code": 0, "data": {"list": [{"user_id": "old"}]}})
        return response({"code": 0, "data": {}})

    async with AsyncAdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        assert (await client.profiles.create(name="x")).id == "p1"
        assert (await client.profiles.update("p1", name="new")).name == "new"
        await client.profiles.delete("p1")
        assert (await client.groups.create("g")).id == "g1"
        assert (await client.groups.list())[0].id == "g1"
        assert (await client.groups.update("g1", name="renamed")).name == "renamed"
        session = await client.browsers.start("p1", headless=True)
        assert session.connection.playwright_cdp == "ws://exact"
        await session.stop()
        await session.stop()
        assert (await client.v1.profiles.create(name="old")).id == "old"
        assert (await client.v1.profiles.list())[0].id == "old"
        await client.v1.profiles.delete("old")
        assert await client.health.check() == {}

    assert paths.count("/api/v2/browser-profile/stop") == 1


@pytest.mark.asyncio
async def test_async_profile_not_found() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return response({"code": 0, "data": {"list": []}})

    async with AsyncAdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ProfileNotFoundError):
            await client.profiles.get("missing")


@pytest.mark.parametrize(
    ("handler", "error"),
    [
        (lambda _: httpx.Response(200, content=b"not-json"), AdsPowerAPIError),
        (lambda _: (_ for _ in ()).throw(httpx.ConnectError("no")), AdsPowerConnectionError),
        (lambda _: (_ for _ in ()).throw(httpx.ReadTimeout("slow")), AdsPowerTimeoutError),
    ],
)
def test_transport_boundary_errors(handler: object, error: type[Exception]) -> None:
    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:  # type: ignore[arg-type]
        with pytest.raises(error):
            client.health.check()


def test_model_and_value_validation() -> None:
    with pytest.raises(ValueError):
        Profile.from_api({"name": "missing id"})
    with pytest.raises(ValueError):
        ScreenResolution.fixed(0, 1080)
    with pytest.raises(ValueError):
        RateLimit(0, 1)


def test_playwright_cleanup_is_idempotent_and_preserves_user_error() -> None:
    calls: list[str] = []

    class Browser:
        def close(self) -> None:
            calls.append("disconnect")
            raise RuntimeError("cleanup")

    session = PlaywrightSession(BrowserConnection(playwright_cdp="ws://exact"), stop=lambda: calls.append("stop"))
    session.browser = Browser()
    session._playwright = type("Runtime", (), {"stop": lambda self: calls.append("runtime")})()
    session.close(preserve_error=True)
    session.close()
    assert calls == ["disconnect", "stop", "runtime"]


@pytest.mark.asyncio
async def test_async_playwright_cleanup_order_and_idempotency() -> None:
    calls: list[str] = []

    class Browser:
        async def close(self) -> None:
            calls.append("disconnect")

    class Runtime:
        async def stop(self) -> None:
            calls.append("runtime")

    async def stop() -> None:
        calls.append("stop")

    session = AsyncPlaywrightSession(BrowserConnection(playwright_cdp="ws://exact"), stop=stop)
    session.browser = Browser()
    session._playwright = Runtime()
    await session.close()
    await session.close()
    assert calls == ["disconnect", "stop", "runtime"]


def test_selenium_adapter_uses_endpoint_without_headless(monkeypatch: pytest.MonkeyPatch) -> None:
    import selenium.webdriver.chrome.options
    import selenium.webdriver.chrome.service
    import selenium.webdriver.chrome.webdriver

    calls: list[object] = []

    class Options:
        def __init__(self) -> None:
            self.arguments: list[str] = []
            self.experimental: dict[str, str] = {}
            self.page_load_strategy: str | None = None

        def add_experimental_option(self, name: str, value: str) -> None:
            self.experimental[name] = value

    class Service:
        def __init__(self, executable_path: str | None = None) -> None:
            calls.append(("service", executable_path))

    class Driver:
        def __init__(self, *, service: object, options: Options) -> None:
            self.options = options
            calls.append(("driver", service))

        def maximize_window(self) -> None:
            calls.append("maximize")

        def quit(self) -> None:
            calls.append("quit")

    monkeypatch.setattr(selenium.webdriver.chrome.options, "Options", Options)
    monkeypatch.setattr(selenium.webdriver.chrome.service, "Service", Service)
    monkeypatch.setattr(selenium.webdriver.chrome.webdriver, "WebDriver", Driver)
    adapter = SeleniumSession(
        BrowserConnection(selenium="remote:9222", webdriver="/driver"),
        stop=lambda: calls.append("stop"),
        start_maximized=True,
        page_load_strategy="eager",
    )
    driver = adapter.__enter__()
    assert driver.options.experimental == {"debuggerAddress": "remote:9222"}
    assert driver.options.arguments == []
    assert driver.options.page_load_strategy == "eager"
    adapter.close()
    adapter.close()
    assert calls[-3:] == ["maximize", "quit", "stop"]


def test_sync_playwright_adapter_uses_exact_cdp(monkeypatch: pytest.MonkeyPatch) -> None:
    import playwright.sync_api

    calls: list[str] = []

    class Browser:
        def close(self) -> None:
            calls.append("browser.close")

    class Chromium:
        def connect_over_cdp(self, endpoint: str) -> Browser:
            calls.append(endpoint)
            return Browser()

    class Runtime:
        chromium = Chromium()

        def stop(self) -> None:
            calls.append("runtime.stop")

    class Starter:
        def start(self) -> Runtime:
            return Runtime()

    monkeypatch.setattr(playwright.sync_api, "sync_playwright", lambda: Starter())
    adapter = PlaywrightSession(
        BrowserConnection(playwright_cdp="ws://remote/exact"),
        stop=lambda: calls.append("profile.stop"),
    )
    with adapter as browser:
        assert isinstance(browser, Browser)
    assert calls == ["ws://remote/exact", "browser.close", "profile.stop", "runtime.stop"]


@pytest.mark.asyncio
async def test_async_playwright_adapter_uses_exact_cdp(monkeypatch: pytest.MonkeyPatch) -> None:
    import playwright.async_api

    calls: list[str] = []

    class Browser:
        async def close(self) -> None:
            calls.append("browser.close")

    class Chromium:
        async def connect_over_cdp(self, endpoint: str) -> Browser:
            calls.append(endpoint)
            return Browser()

    class Runtime:
        chromium = Chromium()

        async def stop(self) -> None:
            calls.append("runtime.stop")

    class Starter:
        async def start(self) -> Runtime:
            return Runtime()

    async def stop() -> None:
        calls.append("profile.stop")

    monkeypatch.setattr(playwright.async_api, "async_playwright", lambda: Starter())
    adapter = AsyncPlaywrightSession(BrowserConnection(playwright_cdp="ws://remote/exact"), stop=stop)
    async with adapter as browser:
        assert isinstance(browser, Browser)
    assert calls == ["ws://remote/exact", "browser.close", "profile.stop", "runtime.stop"]

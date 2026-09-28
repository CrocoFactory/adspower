from __future__ import annotations

import asyncio
import json

import httpx
import pytest

import adspower
from adspower import (
    AdsPowerClient,
    AdsPowerRatePolicy,
    AdsPowerResponseError,
    AdsPowerValidationError,
    AsyncAdsPowerClient,
    RateLimit,
)
from adspower.config import ClientConfig
from adspower.exceptions import AuthenticationError, RateLimitError
from adspower.transport import SyncTransport


def response(payload: object, status: int = 200, headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(status, json=payload, headers=headers)


def test_update_return_contract_is_deterministic() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/update"):
            return response({"code": 0, "data": {"profile_id": "surprise", "name": "server"}})
        return response({"code": 0, "data": {"list": [{"profile_id": "p1", "name": "fresh"}]}})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        assert client.profiles.update("p1", name="renamed") is None
        profile = client.profiles.update("p1", name="renamed", refresh=True)

    assert profile.id == "p1"
    assert profile.name == "fresh"
    assert [request.url.path for request in requests] == [
        "/api/v2/browser-profile/update",
        "/api/v2/browser-profile/update",
        "/api/v2/browser-profile/list",
    ]


@pytest.mark.asyncio
async def test_async_update_return_contract_is_deterministic() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/update"):
            return response({"code": 0, "data": {}})
        return response({"code": 0, "data": {"list": [{"profile_id": "p1"}]}})

    async with AsyncAdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        assert await client.profiles.update("p1", name="renamed") is None
        assert (await client.profiles.update("p1", name="renamed", refresh=True)).id == "p1"

    assert [request.url.path for request in requests].count("/api/v2/browser-profile/list") == 1


@pytest.mark.parametrize("unwrap", [True, False])
@pytest.mark.parametrize(
    ("status", "payload", "error"),
    [
        (401, {"error": "no"}, AuthenticationError),
        (403, {"error": "no"}, AuthenticationError),
        (429, {"error": "slow"}, RateLimitError),
        (200, {"code": -1, "msg": "Too many requests"}, RateLimitError),
    ],
)
def test_unwrap_modes_share_error_classification(
    unwrap: bool,
    status: int,
    payload: dict[str, object],
    error: type[Exception],
) -> None:
    with AdsPowerClient(transport=httpx.MockTransport(lambda _: response(payload, status))) as client:
        with pytest.raises(error):
            client.request("GET", "/status", unwrap=unwrap)


def test_rate_limit_error_exposes_retry_after() -> None:
    with AdsPowerClient(
        transport=httpx.MockTransport(
            lambda _: response({"error": "slow"}, 429, {"Retry-After": "2.5"})
        )
    ) as client:
        with pytest.raises(RateLimitError) as exc:
            client.health.check()
    assert exc.value.retry_after == 2.5


@pytest.mark.parametrize(
    "payload",
    [
        {"code": 0, "data": {"unexpected": "shape"}},
        {"code": 0, "data": {"list": [1]}},
        {"code": 0, "data": {"list": [{}]}},
    ],
)
def test_malformed_profile_responses_fail_closed(payload: dict[str, object]) -> None:
    with AdsPowerClient(transport=httpx.MockTransport(lambda _: response(payload))) as client:
        with pytest.raises(AdsPowerResponseError):
            client.profiles.list()


def test_invalid_json_is_response_error() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=b"not-json"))
    with AdsPowerClient(transport=transport) as client:
        with pytest.raises(AdsPowerResponseError):
            client.health.check()


def test_raw_unwrap_false_requires_object_envelope() -> None:
    with AdsPowerClient(transport=httpx.MockTransport(lambda _: response([1, 2]))) as client:
        with pytest.raises(AdsPowerResponseError):
            client.request("GET", "/api/v2/future", unwrap=False)


def test_global_and_endpoint_rate_limits_are_cumulative() -> None:
    class Recorder:
        def __init__(self, name: str, calls: list[str]) -> None:
            self.name = name
            self.calls = calls

        def acquire(self) -> None:
            self.calls.append(self.name)

    calls: list[str] = []
    transport = SyncTransport(
        ClientConfig.resolve(),
        rate_limit=RateLimit(2, 1),
        endpoint_limits={"/api/v2/browser-profile/cookies": RateLimit(1, 1)},
        transport=httpx.MockTransport(lambda _: response({"code": 0, "data": {"cookies": []}})),
    )
    transport._limiter = Recorder("global", calls)  # type: ignore[assignment]
    transport._endpoint_limiters[(None, "/api/v2/browser-profile/cookies")] = Recorder(  # type: ignore[assignment]
        "endpoint", calls
    )
    transport.request("GET", "/api/v2/browser-profile/cookies?ignored=1")
    transport.close()
    assert calls == ["global", "endpoint"]


def test_ads_power_rate_policy_documents_verified_cookie_exception() -> None:
    policy = AdsPowerRatePolicy.for_profile_count(201)
    assert policy.global_limit == RateLimit(5, 1.0)
    assert policy.endpoint_limits["/api/v2/browser-profile/cookies"] == RateLimit(1, 1.0)
    assert AdsPowerRatePolicy.conservative().global_limit == RateLimit(2, 1.0)


def test_proxy_update_serializes_port_and_public_proxy_type() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return response({"code": 0, "data": {}})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        client.proxies.update("px", proxy_type="http", port=8080)

    assert json.loads(requests[0].content) == {
        "proxy_id": "px",
        "type": "http",
        "port": "8080",
    }


def test_move_and_delete_cache_do_not_invent_100_item_maximum() -> None:
    requests: list[httpx.Request] = []
    ids = [str(index) for index in range(101)]

    with AdsPowerClient(
        transport=httpx.MockTransport(
            lambda request: requests.append(request) or response({"code": 0, "data": {}})
        )
    ) as client:
        client.profiles.move(ids, "g")
        client.profiles.delete_cache(ids, ["cookie"])

    assert len(json.loads(requests[0].content)["user_ids"]) == 101
    assert len(json.loads(requests[1].content)["profile_id"]) == 101


def test_page_and_share_validation() -> None:
    with AdsPowerClient(
        transport=httpx.MockTransport(lambda _: response({"code": 0, "data": {"list": []}}))
    ) as client:
        with pytest.raises(AdsPowerValidationError):
            client.profiles.list(page=0)
        with pytest.raises(AdsPowerValidationError):
            client.profiles.find_by_name("x", max_pages=0)
        with pytest.raises(AdsPowerValidationError):
            client.profiles.share(["p"], "receiver", share_type=3)


def test_browser_start_typed_options_and_extra_escape_hatch() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return response({"code": 0, "data": {"debug_port": 9222}})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        client.browsers.start(
            "p",
            last_opened_tabs=True,
            proxy_detection=0,
            cdp_mask="1",
            device_scale=1.25,
            extra_options={"future_option": "x"},
        )

    body = json.loads(requests[0].content)
    assert body["last_opened_tabs"] == "1"
    assert body["proxy_detection"] == "0"
    assert body["cdp_mask"] == "1"
    assert body["device_scale"] == 1.25
    assert body["future_option"] == "x"


def test_browser_host_override_and_exact_policy() -> None:
    remote = adspower.BrowserConnection.from_api(
        {
            "ws": {
                "selenium": "127.0.0.1:9222",
                "puppeteer": "ws://127.0.0.1:9222/devtools/browser/id",
            }
        },
        base_url="http://api.internal:50325",
        browser_host="browser.internal",
    )
    assert remote.selenium_debugger_address == "browser.internal:9222"
    assert remote.playwright_cdp_url == "ws://browser.internal:9222/devtools/browser/id"

    exact = adspower.BrowserConnection.from_api(
        {"ws": {"puppeteer": "ws://127.0.0.1:9222/devtools/browser/id"}},
        base_url="http://api.internal:50325",
        endpoint_policy="exact",
    )
    assert exact.playwright_cdp_url == "ws://127.0.0.1:9222/devtools/browser/id"


def test_public_exception_hierarchy_is_exported_from_package_root() -> None:
    expected = {
        "AdsPowerError",
        "AdsPowerValidationError",
        "AdsPowerConfigurationError",
        "AdsPowerTransportError",
        "AdsPowerConnectionError",
        "AdsPowerTimeoutError",
        "AdsPowerAPIError",
        "AdsPowerResponseError",
        "AuthenticationError",
        "RateLimitError",
        "ProfileNotFoundError",
    }
    assert all(hasattr(adspower, name) for name in expected)


@pytest.mark.asyncio
async def test_async_playwright_cleanup_preserves_task_cancellation() -> None:
    from adspower.automation import AsyncPlaywrightSession
    from adspower.models import BrowserConnection

    class Browser:
        async def close(self) -> None:
            return None

    class Runtime:
        async def stop(self) -> None:
            return None

    async def cancelled_stop() -> None:
        raise asyncio.CancelledError

    session = AsyncPlaywrightSession(
        BrowserConnection(playwright_cdp_url="ws://exact"),
        stop=cancelled_stop,
    )
    session.browser = Browser()
    session._playwright = Runtime()

    with pytest.raises(asyncio.CancelledError):
        await session.close()

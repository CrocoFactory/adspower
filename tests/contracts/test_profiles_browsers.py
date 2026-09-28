from __future__ import annotations

import json

import httpx
import pytest

from adspower import (
    AdsPowerClient,
    AdsPowerNotFoundError,
    AdsPowerProtocolError,
    AdsPowerValidationError,
    AsyncAdsPowerClient,
    FingerprintConfig,
)


def envelope(data: object = None) -> httpx.Response:
    return httpx.Response(200, json={"code": 0, "msg": "ok", "data": data})


def request_json(request: httpx.Request) -> object:
    return json.loads(request.content.decode()) if request.content else None


def test_profile_create_list_update_and_lookup_contract() -> None:
    requests: list[tuple[str, str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request_json(request)
        requests.append((request.method, request.url.path, body))
        if request.url.path.endswith("/create"):
            return envelope({"profile_id": "p1", "profile_no": "42"})
        if request.url.path.endswith("/list"):
            assert body["limit"] in {1, 100}
            return envelope(
                {
                    "list": [{"profile_id": "p1", "profile_no": "42", "name": "shop"}],
                    "page": 1,
                    "page_size": body["limit"],
                    "total_count": 1,
                    "total_pages": 1,
                }
            )
        return envelope({})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        created = client.profiles.create(name="shop", fingerprint_config=FingerprintConfig())
        assert created.profile_id == "p1"
        create_body = requests[0][2]
        assert create_body["user_proxy_config"] == {"proxy_soft": "no_proxy"}
        assert create_body["fingerprint_config"] == {}

        page = client.profiles.list(
            name="shop",
            name_filter="include",
            tag_ids=["tag1"],
            tags_filter="exclude",
        )
        assert page.total_count == 1
        assert page.items[0].profile_id == "p1"
        list_body = requests[1][2]
        assert list_body["limit"] == 100
        assert list_body["name_filter"] == "include"
        assert list_body["tag_ids"] == ["tag1"]

        assert client.profiles.update("p1", name="renamed") is None
        assert requests[-1][1].endswith("/update")
        assert len([item for item in requests if item[1].endswith("/list")]) == 1

        profile = client.profiles.get("p1")
        assert profile.profile_no == "42"


def test_profile_list_rejects_bad_pagination_and_missing_get() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return envelope({"list": [], "page": 1, "page_size": 1, "total_count": 0, "total_pages": 0})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AdsPowerValidationError):
            client.profiles.list(page_size=201)
        with pytest.raises(AdsPowerNotFoundError):
            client.profiles.get("missing")


def test_profile_protocol_error_for_malformed_known_field() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return envelope({"list": [{"profile_id": "p1", "name": {"bad": True}}]})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AdsPowerProtocolError):
            client.profiles.list()


def test_browser_start_omits_defaults_and_session_owns_stop() -> None:
    requests: list[tuple[str, str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request_json(request)
        requests.append((request.method, request.url.path, body))
        if request.url.path.endswith("/start"):
            return envelope(
                {
                    "ws": {
                        "selenium": "127.0.0.1:9222",
                        "puppeteer": "ws://127.0.0.1:9222/devtools/browser/abc",
                    },
                    "debug_port": 9222,
                }
            )
        return envelope({})

    with AdsPowerClient(
        base_url="http://10.0.0.2:50325",
        transport=httpx.MockTransport(handler),
    ) as client:
        with client.browsers.session("p1", start_maximized=True) as session:
            assert session.connection.selenium_debugger_address == "127.0.0.1:9222"
            assert session.connection.playwright_cdp_url == "ws://127.0.0.1:9222/devtools/browser/abc"
        start_body = requests[0][2]
        assert "headless" not in start_body
        assert start_body["launch_args"] == ["--start-maximized"]
        assert requests[-1][1].endswith("/stop")


def test_raw_rejects_absolute_urls_and_returns_envelope() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return envelope({"value": 1})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        assert client.raw.request("GET", "/api/future").data == {"value": 1}
        with pytest.raises(AdsPowerValidationError):
            client.raw.request("GET", "https://evil.example/api")


@pytest.mark.asyncio
async def test_sync_async_profile_list_payload_parity() -> None:
    sync_bodies: list[object] = []
    async_bodies: list[object] = []

    def sync_handler(request: httpx.Request) -> httpx.Response:
        sync_bodies.append(request_json(request))
        return envelope({"list": [], "page": 1, "page_size": 200, "total_pages": 0})

    async def async_handler(request: httpx.Request) -> httpx.Response:
        async_bodies.append(request_json(request))
        return envelope({"list": [], "page": 1, "page_size": 200, "total_pages": 0})

    with AdsPowerClient(transport=httpx.MockTransport(sync_handler)) as client:
        client.profiles.list(name="x", tag_ids=["t"])
    async with AsyncAdsPowerClient(transport=httpx.MockTransport(async_handler)) as client:
        await client.profiles.list(name="x", tag_ids=["t"])

    assert sync_bodies == async_bodies

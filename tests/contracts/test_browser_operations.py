from __future__ import annotations

import json

import httpx
import pytest

from adspower import AdsPowerClient, AdsPowerProtocolError, AdsPowerValidationError
from adspower.models.browsers import parse_browser_connection, parse_browser_status


def ok(data: object = None) -> httpx.Response:
    return httpx.Response(200, json={"code": 0, "msg": "ok", "data": data})


def test_browser_status_lists_cloud_and_stop_all() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        seen.append(path)
        if path.endswith("/active") and "cloud" not in path:
            return ok({"status": "Inactive"})
        if path.endswith("/local-active"):
            return ok(
                {
                    "list": [
                        {
                            "profile_id": "p1",
                            "ws": {"selenium": "127.0.0.1:9222"},
                            "debug_port": 9222,
                        }
                    ]
                }
            )
        if path.endswith("/cloud-active"):
            return ok({"list": [{"profile_id": "p1", "status": "Inactive"}]})
        return ok({})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        assert not client.browsers.status("p1").active
        assert client.browsers.list_opened()[0].profile_id == "p1"
        assert client.browsers.cloud_status(["p1"])[0].status == "Inactive"
        client.browsers.stop_all()

    assert "/api/v2/browser-profile/stop-all" in seen


def test_start_payload_variants_and_validation() -> None:
    captured: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content.decode()))
        return ok({"ws": {"selenium": "127.0.0.1:9222"}, "debug_port": 9222})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        session = client.browsers.start(
            profile_no="1",
            ip_tab=False,
            launch_args=["--foo"],
            headless=False,
            last_opened_tabs=True,
            proxy_detection=False,
            password_filling=True,
            password_saving=False,
            delete_cache=True,
            cdp_mask=False,
            device_scale=1.25,
        )
        assert session.connection.debug_port == 9222

    payload = captured[0]
    assert payload["profile_no"] == "1"
    assert payload["headless"] == "0"
    assert payload["last_opened_tabs"] == "1"
    assert payload["device_scale"] == 1.25

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AdsPowerValidationError):
            client.browsers.start()
        with pytest.raises(AdsPowerValidationError):
            client.browsers.start("p", profile_no="1")


def test_browser_parsers_cover_status_and_protocol_failures() -> None:
    connection = parse_browser_connection(
        {
            "ws": {"puppeteer": "ws://127.0.0.1/devtools/browser/id"},
            "webdriver": "/tmp/driver",
            "marionette_port": "2828",
            "marionette_host": "localhost",
            "future": 1,
        }
    )
    assert connection.playwright_cdp_url
    assert connection.marionette_port == 2828
    assert connection.extra == {"future": 1}

    assert parse_browser_status({"status": "Active", "debug_port": 9222}).active
    with pytest.raises(AdsPowerProtocolError):
        parse_browser_connection({})
    with pytest.raises(AdsPowerProtocolError):
        parse_browser_status({})

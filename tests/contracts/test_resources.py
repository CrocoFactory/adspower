from __future__ import annotations

import json

import httpx
import pytest

from adspower import AdsPowerClient, StoredProxyConfig, TagCreate, TagUpdate


def request_json(request: httpx.Request) -> object:
    return json.loads(request.content.decode()) if request.content else None


def test_resource_namespaces_cover_verified_endpoints() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        path = request.url.path
        body = request_json(request)
        if path == "/status":
            return httpx.Response(200, json={"status": "ok"})
        if path.endswith("/group/create"):
            return httpx.Response(200, json={"code": 0, "data": {"group_id": "g1", "group_name": "n"}})
        if path.endswith("/group/list"):
            return httpx.Response(200, json={"code": 0, "data": {"list": [], "page": 1, "page_size": 10}})
        if path.endswith("/category/list"):
            return httpx.Response(200, json={"code": 0, "data": {"list": [], "page": 1, "page_size": 10}})
        if path.endswith("/proxy-list/create"):
            assert isinstance(body, list)
            return httpx.Response(200, json={"code": 0, "data": {"proxy_id": ["px1"]}})
        if path.endswith("/proxy-list/list"):
            return httpx.Response(200, json={"code": 0, "data": {"list": [], "page": 1, "page_size": 50}})
        if path.endswith("/browser-tags/list"):
            return httpx.Response(200, json={"code": 0, "data": {"list": [], "page": 1, "page_size": 50}})
        if path.endswith("/kernels"):
            return httpx.Response(200, json={"code": 0, "data": []})
        return httpx.Response(200, json={"code": 0, "data": {}})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        assert client.health.status()["status"] == "ok"
        assert client.groups.create("n").group_id == "g1"
        client.groups.update("g1", name="new")
        assert client.groups.list(page_size=10).items == ()
        assert client.categories.list(page_size=10).items == ()

        ids = client.proxies.create(StoredProxyConfig("http", "127.0.0.1", 8080))
        assert ids == ("px1",)
        client.proxies.update("px1", remark="r")
        assert client.proxies.list().items == ()
        client.proxies.delete("px1")

        assert client.tags.list().items == ()
        client.tags.create([TagCreate("a", "blue")])
        client.tags.update([TagUpdate("t1", name="b")])
        client.tags.delete(["t1"])

        assert client.kernels.list() == ()
        client.kernels.download("Chrome", "141")
        client.app.update_patch("beta")

    assert "/api/v2/browser-profile/update-patch" in seen


@pytest.mark.parametrize(
    "config",
    [
        StoredProxyConfig("http", "127.0.0.1", 0),
        StoredProxyConfig("https", "::1", "65536"),
        StoredProxyConfig("ssh", "host", 22),
        StoredProxyConfig("socks5", "host", 1080),
    ],
)
def test_stored_proxy_config_serialization(config: StoredProxyConfig) -> None:
    payload = config.to_api()
    assert payload["type"] == config.proxy_type
    assert isinstance(payload["port"], str)


def test_stored_proxy_validation() -> None:
    with pytest.raises(Exception):
        StoredProxyConfig("http", "", 80)
    with pytest.raises(Exception):
        StoredProxyConfig("http", "host", 99999)

from __future__ import annotations

import json

import httpx
import pytest

from adspower import AsyncAdsPowerClient, StoredProxyConfig, TagCreate, TagUpdate


def request_json(request: httpx.Request) -> object:
    return json.loads(request.content.decode()) if request.content else None


def ok(data: object = None) -> httpx.Response:
    return httpx.Response(200, json={"code": 0, "msg": "ok", "data": data})


@pytest.mark.asyncio
async def test_async_resource_surface_and_parity() -> None:
    seen: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        seen.append(path)
        body = request_json(request)

        if path == "/status":
            return httpx.Response(200, json={"status": "ok"})
        if path.endswith("/browser-profile/create"):
            return ok({"profile_id": "p1", "profile_no": "1"})
        if path.endswith("/browser-profile/list"):
            name = body.get("name") if isinstance(body, dict) else None
            profile_ids = body.get("profile_id") if isinstance(body, dict) else None
            items = []
            if name == "match":
                items = [{"profile_id": "p1", "name": "match"}]
            elif profile_ids:
                items = [{"profile_id": str(profile_ids[0]), "name": "found"}]
            return ok(
                {
                    "list": items,
                    "page": body.get("page", 1),
                    "page_size": body.get("limit", 200),
                    "total_count": len(items),
                    "total_pages": 1 if items else 0,
                }
            )
        if path.endswith("/browser-profile/cookies"):
            return ok({"cookies": [{"name": "a", "value": "b"}]})
        if path.endswith("/browser-profile/ua"):
            return ok({"p1": "UA"})
        if path.endswith("/browser-profile/new-fingerprint"):
            return ok({"p1": True})
        if path.endswith("/browser-profile/start"):
            return ok(
                {
                    "ws": {
                        "selenium": "127.0.0.1:9222",
                        "puppeteer": "ws://127.0.0.1:9222/devtools/browser/id",
                    },
                    "debug_port": 9222,
                }
            )
        if path.endswith("/browser-profile/active"):
            return ok(
                {
                    "status": "Active",
                    "ws": {"selenium": "127.0.0.1:9222"},
                    "debug_port": 9222,
                }
            )
        if path.endswith("/browser/local-active"):
            return ok(
                [
                    {
                        "profile_id": "p1",
                        "ws": {"selenium": "127.0.0.1:9222"},
                        "debug_port": 9222,
                    }
                ]
            )
        if path.endswith("/browser/cloud-active"):
            return ok([{"profile_id": "p1", "status": "Active"}])
        if path.endswith("/group/create"):
            return ok({"group_id": "g1", "group_name": "group"})
        if path.endswith("/group/list"):
            return ok({"list": [{"group_id": "g1", "group_name": "group"}], "page": 1, "page_size": 10})
        if path.endswith("/category/list"):
            return ok({"list": [{"category_id": "c1", "category_name": "cat"}], "page": 1, "page_size": 10})
        if path.endswith("/proxy-list/create"):
            return ok({"proxy_id": ["px1"]})
        if path.endswith("/proxy-list/list"):
            return ok({"list": [{"proxy_id": "px1", "type": "http"}], "page": 1, "page_size": 50})
        if path.endswith("/browser-tags/list"):
            return ok({"list": [{"id": "t1", "name": "tag"}], "page": 1, "page_size": 50})
        if path.endswith("/browser-profile/kernels"):
            return ok([{"kernel_type": "Chrome", "kernel_version": "141"}])
        if path.endswith("/future"):
            return ok({"future": True})
        return ok({})

    transport = httpx.MockTransport(handler)
    async with AsyncAdsPowerClient(
        base_url="http://10.0.0.2:50325",
        transport=transport,
    ) as client:
        created = await client.profiles.create(name="n")
        assert created.profile_id == "p1"
        assert await client.profiles.update("p1", name="n2") is None

        page = await client.profiles.list(name="match")
        assert page.items[0].name == "match"
        assert (await client.profiles.get("p1")).profile_id == "p1"
        assert (await client.profiles.find_by_name("match")).name == "match"

        await client.profiles.delete("p1")
        await client.profiles.delete_many(["p1", "p2"])
        await client.profiles.move(["p1"], "g1")
        assert (await client.profiles.cookies(profile_id="p1"))[0]["name"] == "a"
        assert (await client.profiles.user_agents(profile_ids=["p1"])) == {"p1": "UA"}
        assert (await client.profiles.new_fingerprint(profile_nos=["1"])) == {"p1": True}
        await client.profiles.delete_cache(["p1"], ["cookie"])
        await client.profiles.share(["p1"], "x@example.test")

        session = await client.browsers.start("p1", headless=True)
        assert session.connection.selenium_debugger_address == "10.0.0.2:9222"
        await session.stop()
        await client.browsers.stop(profile_no="1")
        await client.browsers.stop_all()
        status = await client.browsers.status("p1")
        assert status.active
        assert (await client.browsers.list_opened())[0].profile_id == "p1"
        assert (await client.browsers.cloud_status(["p1"]))[0].status == "Active"

        assert (await client.groups.create("group")).group_id == "g1"
        await client.groups.update("g1", name="new")
        assert (await client.groups.list(page_size=10)).items[0].group_id == "g1"
        assert (await client.categories.list(page_size=10)).items[0].category_id == "c1"

        assert await client.proxies.create(StoredProxyConfig("http", "host", 8080)) == ("px1",)
        assert await client.proxies.create_many([StoredProxyConfig("http", "host", 8081)]) == ("px1",)
        await client.proxies.update("px1", remark="new")
        assert (await client.proxies.list()).items[0].proxy_id == "px1"
        await client.proxies.delete("px1")
        await client.proxies.delete_many(["px1"])

        assert (await client.tags.list()).items[0].tag_id == "t1"
        await client.tags.create([TagCreate("tag")])
        await client.tags.update([TagUpdate("t1", color="blue")])
        await client.tags.delete(["t1"])

        assert (await client.kernels.list())[0].version == "141"
        await client.kernels.download("Chrome", "141")
        await client.app.update_patch()
        assert (await client.health.status())["status"] == "ok"
        assert (await client.raw.request("POST", "/future", json={"x": 1})).data == {"future": True}

    assert "/api/v2/browser-profile/stop-all" in seen


@pytest.mark.asyncio
async def test_async_iter_all_stops_on_short_page() -> None:
    pages: list[int] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body = request_json(request)
        page = body["page"]
        pages.append(page)
        items = [{"profile_id": f"p{page}"}] if page == 1 else []
        return ok({"list": items, "page": page, "page_size": 2})

    async with AsyncAdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        values = [profile.profile_id async for profile in client.profiles.iter_all(page_size=2)]

    assert values == ["p1"]
    assert pages == [1]

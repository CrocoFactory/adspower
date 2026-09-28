from __future__ import annotations

import json

import httpx
import pytest

from adspower import AdsPowerClient, AdsPowerProtocolError, AdsPowerValidationError


def body(request: httpx.Request) -> object:
    return json.loads(request.content.decode()) if request.content else None


def ok(data: object = None) -> httpx.Response:
    return httpx.Response(200, json={"code": 0, "msg": "ok", "data": data})


def test_all_profile_operations_and_iteration() -> None:
    requests: list[tuple[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = body(request)
        requests.append((request.url.path, payload))
        path = request.url.path
        if path.endswith("/list"):
            page = payload.get("page", 1)
            if page == 1:
                return ok(
                    {
                        "list": [{"profile_id": "p1", "name": "exact"}],
                        "page": 1,
                        "page_size": 1,
                        "total_pages": 2,
                    }
                )
            return ok(
                {
                    "list": [{"profile_id": "p2"}],
                    "page": 2,
                    "page_size": 1,
                    "total_pages": 2,
                }
            )
        if path.endswith("/cookies"):
            return ok({"cookie": '[{"name":"a","value":"1"}]'})
        if path.endswith("/ua"):
            return ok(["UA1"])
        return ok({"done": True})

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        assert [p.profile_id for p in client.profiles.iter_all(page_size=1)] == ["p1", "p2"]
        assert client.profiles.find_by_name("exact").profile_id == "p1"
        client.profiles.delete_many(["p1", "p2"])
        client.profiles.move(["p1", "p2"], "g1")
        assert client.profiles.cookies(profile_no="1")[0]["value"] == "1"
        assert client.profiles.user_agents(profile_nos=["1"]) == ["UA1"]
        assert client.profiles.new_fingerprint(profile_ids=["p1"]) == {"done": True}
        client.profiles.delete_cache(["p1"], ["cookie", "history"])
        assert client.profiles.share(
            ["p1"],
            "+100000",
            share_type="phone",
            content=["name", "proxy"],
        ) == {"done": True}

    paths = [path for path, _ in requests]
    assert "/api/v1/user/regroup" in paths
    assert "/api/v2/browser-profile/share" in paths


@pytest.mark.parametrize(
    "call",
    [
        lambda client: client.profiles.user_agents(),
        lambda client: client.profiles.user_agents(profile_ids=["p"], profile_nos=["1"]),
        lambda client: client.profiles.new_fingerprint(),
        lambda client: client.profiles.delete_cache(["p"], []),
        lambda client: client.profiles.delete_many([]),
        lambda client: client.profiles.share([], "x@example.test"),
    ],
)
def test_profile_operation_validation(call) -> None:
    with AdsPowerClient(transport=httpx.MockTransport(lambda request: ok({}))) as client:
        with pytest.raises(AdsPowerValidationError):
            call(client)


def test_cookie_parser_rejects_invalid_json_and_items() -> None:
    responses = iter(
        [
            ok({"cookies": "not-json"}),
            ok({"cookies": ["not-an-object"]}),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    with AdsPowerClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AdsPowerProtocolError):
            client.profiles.cookies(profile_id="p")
        with pytest.raises(AdsPowerProtocolError):
            client.profiles.cookies(profile_id="p")

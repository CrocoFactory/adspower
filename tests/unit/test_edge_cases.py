from __future__ import annotations

import httpx
import pytest

from adspower import (
    AdsPowerClient,
    AdsPowerConfigurationError,
    AdsPowerProtocolError,
    AdsPowerValidationError,
    AsyncAdsPowerClient,
    FingerprintConfig,
    InlineProxyConfig,
    PlatformAccount,
    StoredProxyConfig,
    TagCreate,
    TagUpdate,
)
from adspower._json import require_json_value
from adspower._security import redact_sensitive, redact_url_credentials
from adspower.models.proxies import parse_proxy
from adspower.protocol import decode_response
from adspower.resources._common import id_list, parse_page, validate_page
from adspower.resources.profiles import _profile_fields
from adspower.resources.proxies import _created_proxy_ids


def ok(data: object = None) -> httpx.Response:
    return httpx.Response(200, json={"code": 0, "msg": "ok", "data": data})


def test_profile_field_serializer_covers_all_typed_branches() -> None:
    payload = _profile_fields(
        {
            "user_proxy_config": InlineProxyConfig.no_proxy(),
            "fingerprint_config": FingerprintConfig(),
            "platform_account": PlatformAccount("example.com", "user"),
            "ignore_cookie_error": True,
            "repeat_config": 2,
            "tags_update_type": "append",
            "tabs": ["https://example.com"],
            "profile_tag_ids": ["t1"],
            "launch_args": ["--foo"],
            "remark": "r",
            "unused": None,
        },
        create=False,
    )
    assert payload["ignore_cookie_error"] == "1"
    assert payload["repeat_config"] == "2"
    assert payload["tags_update_type"] == "2"
    assert payload["launch_args"] == ["--foo"]

    assert _profile_fields({"launch_args": "--foo"}, create=False)["launch_args"] == "--foo"

    invalid = [
        {"user_proxy_config": object()},
        {"fingerprint_config": object()},
        {"platform_account": object()},
        {"ignore_cookie_error": "yes"},
        {"repeat_config": 1},
        {"tags_update_type": "bad"},
        {"tabs": "not-a-sequence-value"},
        {"launch_args": object()},
        {"other": object()},
    ]
    for fields in invalid:
        with pytest.raises(AdsPowerValidationError):
            _profile_fields(fields, create=False)


def test_common_validation_and_page_protocol_edges() -> None:
    with pytest.raises(AdsPowerValidationError):
        id_list("abc", name="ids")
    with pytest.raises(AdsPowerValidationError):
        id_list([""], name="ids")
    with pytest.raises(AdsPowerValidationError):
        id_list(["a", "b"], name="ids", maximum=1)
    with pytest.raises(AdsPowerValidationError):
        validate_page(0, 1, maximum=10)
    with pytest.raises(AdsPowerValidationError):
        validate_page(1, 11, maximum=10)

    parser = lambda item: item
    assert parse_page(
        [{"x": 1}],
        item_keys=("items",),
        parser=parser,
        requested_page=1,
        requested_page_size=10,
    ).items == ({"x": 1},)

    bad_pages = [
        {},
        {"items": [], "page": 0},
        {"items": [], "page_size": 0},
        {"items": [], "total_count": -1},
        {"items": [], "total_pages": -1},
    ]
    for page in bad_pages:
        with pytest.raises(AdsPowerProtocolError):
            parse_page(
                page,
                item_keys=("items",),
                parser=parser,
                requested_page=1,
                requested_page_size=10,
            )


def test_protocol_misc_branches() -> None:
    request = httpx.Request("GET", "http://example.test")
    response = httpx.Response(
        429,
        headers={"Retry-After": "not-a-number"},
        request=request,
    )
    from adspower import AdsPowerRateLimitError

    with pytest.raises(AdsPowerRateLimitError) as caught:
        decode_response(response, method="GET", path="/x")
    assert caught.value.retry_after is None

    plain = httpx.Response(200, json={"status": "ok"}, request=request)
    assert decode_response(
        plain,
        method="GET",
        path="/status",
        allow_plain_object=True,
    ).data == {"status": "ok"}

    assert decode_response(
        httpx.Response(200, json={"code": "0", "msg": None}, request=request),
        method="GET",
        path="/x",
    ).message == ""

    with pytest.raises(AdsPowerProtocolError):
        decode_response(
            httpx.Response(200, json={"code": True}, request=request),
            method="GET",
            path="/x",
        )


def test_json_and_security_misc_branches() -> None:
    assert require_json_value([{"x": True}, 1, 1.5, None], field="x") == [
        {"x": True},
        1,
        1.5,
        None,
    ]
    with pytest.raises(AdsPowerProtocolError):
        require_json_value({1: "bad"}, field="x")
    with pytest.raises(AdsPowerProtocolError):
        require_json_value(object(), field="x")

    assert redact_sensitive(("a", {"token": "secret"})) == (
        "a",
        {"token": "<redacted>"},
    )
    assert redact_url_credentials(None) is None
    assert redact_url_credentials("http://example.test/path") == "http://example.test/path"


def test_proxy_parser_and_create_id_edges() -> None:
    proxy = parse_proxy(
        {
            "proxy_id": 1,
            "type": "http",
            "proxy_port": 8080,
            "proxy_password": "secret",
            "related_profile_no": [1, "2"],
            "proxy_tags": [{"id": "t"}],
            "future": True,
        }
    )
    assert proxy.port == "8080"
    assert proxy.related_profile_no == ("1", "2")
    assert "secret" not in repr(proxy)

    with pytest.raises(AdsPowerProtocolError):
        parse_proxy({"proxy_id": "p", "proxy_port": []})
    with pytest.raises(AdsPowerProtocolError):
        _created_proxy_ids({"proxy_id": []})
    with pytest.raises(AdsPowerProtocolError):
        _created_proxy_ids({"proxy_id": [None]})


def test_tag_and_proxy_public_validation() -> None:
    with pytest.raises(AdsPowerValidationError):
        TagCreate("").to_api()
    with pytest.raises(AdsPowerValidationError):
        TagCreate("x" * 51).to_api()
    assert TagCreate("tag", "green").to_api()["color"] == "green"
    with pytest.raises(AdsPowerValidationError):
        TagUpdate("t", name="").to_api()

    with pytest.raises(AdsPowerValidationError):
        StoredProxyConfig("http", "host", "abc")
    with pytest.raises(AdsPowerValidationError):
        StoredProxyConfig("http", "host", 65536)


def test_config_environment_and_client_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADSPOWER_BROWSER_START_TIMEOUT", "bad")
    with pytest.raises(AdsPowerConfigurationError):
        AdsPowerClient()

    monkeypatch.delenv("ADSPOWER_BROWSER_START_TIMEOUT")
    monkeypatch.setenv("ADSPOWER_BROWSER_ENDPOINT_POLICY", "bad")
    with pytest.raises(AdsPowerConfigurationError):
        AdsPowerClient()

    monkeypatch.delenv("ADSPOWER_BROWSER_ENDPOINT_POLICY")
    with pytest.raises(AdsPowerValidationError):
        AdsPowerClient(
            rate_limit=None,
            endpoint_limits={"/x": __import__("adspower").RateLimit()},
            rate_policy=__import__("adspower").AdsPowerRatePolicy.conservative(),
        )


@pytest.mark.asyncio
async def test_async_profile_list_validation_edges() -> None:
    async with AsyncAdsPowerClient(
        transport=httpx.MockTransport(lambda request: ok({"list": []}))
    ) as client:
        with pytest.raises(AdsPowerValidationError):
            await client.profiles.list(page="one")
        with pytest.raises(AdsPowerValidationError):
            await client.profiles.list(unknown=True)
        with pytest.raises(AdsPowerValidationError):
            await client.profiles.list(profile_id=object())
        with pytest.raises(AdsPowerValidationError):
            await client.profiles.user_agents()
        with pytest.raises(AdsPowerValidationError):
            await client.profiles.new_fingerprint()
        with pytest.raises(AdsPowerValidationError):
            await client.profiles.delete_cache(["p"], [])

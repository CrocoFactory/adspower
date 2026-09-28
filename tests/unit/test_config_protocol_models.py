from __future__ import annotations

import httpx
import pytest

from adspower import (
    AdsPowerAPIError,
    AdsPowerAuthenticationError,
    AdsPowerConfig,
    AdsPowerConfigurationError,
    AdsPowerProtocolError,
    AdsPowerRateLimitError,
    AdsPowerValidationError,
    FingerprintConfig,
    InlineProxyConfig,
    MacAddressConfig,
    MediaDevicesConfig,
    ScreenResolution,
    WebGLConfig,
)
from adspower._json import optional_int, require_id_string, require_object
from adspower.models.profiles import parse_profile
from adspower.protocol import decode_response


def response(status: int, payload: object, *, headers: dict[str, str] | None = None) -> httpx.Response:
    request = httpx.Request("POST", "http://127.0.0.1/api")
    return httpx.Response(status, json=payload, headers=headers, request=request)


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("ftp://example.test", "http or https"),
        ("http:///missing", "host"),
        ("http://user:pass@example.test", "credentials"),
        ("http://example.test/path", "path"),
        ("http://example.test/?x=1", "query"),
    ],
)
def test_config_rejects_unsafe_base_urls(url: str, message: str) -> None:
    with pytest.raises(AdsPowerConfigurationError, match=message):
        AdsPowerConfig.resolve(base_url=url)


def test_config_normalizes_and_redacts() -> None:
    config = AdsPowerConfig.resolve(
        base_url="http://[::1]:50325/",
        api_key=" secret ",
        browser_host="[2001:db8::1]",
        timeout=1.0,
    )
    assert config.base_url == "http://[::1]:50325"
    assert config.browser_host == "2001:db8::1"
    assert config.headers == {"Authorization": "Bearer secret"}
    assert "secret" not in repr(config)


def test_config_rejects_host_with_port_and_bad_timeout() -> None:
    with pytest.raises(AdsPowerConfigurationError):
        AdsPowerConfig.resolve(browser_host="localhost:9222")
    with pytest.raises(AdsPowerConfigurationError):
        AdsPowerConfig.resolve(timeout=0)


def test_protocol_success_and_business_error() -> None:
    envelope = decode_response(response(200, {"code": 0, "msg": "ok", "data": {"x": 1}}), method="POST", path="/x")
    assert envelope.code == 0
    assert envelope.data == {"x": 1}

    with pytest.raises(AdsPowerAPIError) as caught:
        decode_response(response(200, {"code": 123, "msg": "arbitrary"}), method="POST", path="/x")
    assert type(caught.value) is AdsPowerAPIError
    assert caught.value.code == 123
    assert caught.value.server_message == "arbitrary"


def test_protocol_http_classification_is_not_message_based() -> None:
    with pytest.raises(AdsPowerAuthenticationError):
        decode_response(response(401, {"message": "anything"}), method="GET", path="/x")
    with pytest.raises(AdsPowerRateLimitError) as caught:
        decode_response(
            response(429, {"message": "anything"}, headers={"Retry-After": "2.5"}),
            method="GET",
            path="/x",
        )
    assert caught.value.retry_after == 2.5

    with pytest.raises(AdsPowerAPIError) as generic:
        decode_response(response(500, {"message": "auth rate limit not found"}), method="GET", path="/x")
    assert type(generic.value) is AdsPowerAPIError


def test_protocol_rejects_malformed_responses() -> None:
    request = httpx.Request("GET", "http://127.0.0.1/x")
    with pytest.raises(AdsPowerProtocolError):
        decode_response(httpx.Response(200, content=b"not json", request=request), method="GET", path="/x")
    with pytest.raises(AdsPowerProtocolError):
        decode_response(response(200, []), method="GET", path="/x")
    with pytest.raises(AdsPowerProtocolError):
        decode_response(response(200, {"code": "abc"}), method="GET", path="/x")
    with pytest.raises(AdsPowerProtocolError):
        decode_response(response(200, {"code": 0, "msg": 123}), method="GET", path="/x")


def test_json_helpers_are_strict() -> None:
    assert optional_int("12", field="n") == 12
    assert require_id_string(12, field="id") == "12"
    with pytest.raises(AdsPowerProtocolError):
        optional_int("x", field="n")
    with pytest.raises(AdsPowerProtocolError):
        require_object(["x"], field="obj")


def test_profile_known_fields_are_not_silently_stringified() -> None:
    profile = parse_profile({"profile_id": 123, "profile_no": 7, "name": "n", "future": {"x": 1}})
    assert profile.profile_id == "123"
    assert profile.profile_no == "7"
    assert profile.extra == {"future": {"x": 1}}
    assert not hasattr(profile, "number")
    with pytest.raises(AdsPowerProtocolError):
        parse_profile({"profile_id": "id", "name": {"wrong": True}})


def test_config_models_validate_and_serialize() -> None:
    assert ScreenResolution.fixed(1280, 720) == "1280_720"
    with pytest.raises(ValueError):
        ScreenResolution.fixed(0, 720)
    with pytest.raises(AdsPowerValidationError):
        WebGLConfig("", "renderer")
    with pytest.raises(AdsPowerValidationError):
        MediaDevicesConfig(0, 1, 1)
    with pytest.raises(AdsPowerValidationError):
        MacAddressConfig("custom")

    proxy = InlineProxyConfig.no_proxy()
    assert proxy.to_api() == {"proxy_soft": "no_proxy"}

    fp = FingerprintConfig(
        automatic_timezone=True,
        screen_resolution="1280_720",
        webgl_mode="custom",
        webgl=WebGLConfig("Vendor", "Renderer"),
    )
    assert fp.to_api()["automatic_timezone"] == "1"
    assert fp.to_api()["webgl"] == "2"

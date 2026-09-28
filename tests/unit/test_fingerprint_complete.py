from __future__ import annotations

import pytest

from adspower import AdsPowerValidationError
from adspower.models.fingerprint import (
    BrowserKernelConfig,
    FingerprintConfig,
    MacAddressConfig,
    MediaDevicesConfig,
    PlatformAccount,
    RandomUserAgentConfig,
    WebGLConfig,
    WebGPUConfig,
)


def test_nested_fingerprint_models_serialize_all_modes() -> None:
    assert WebGPUConfig("real").to_api() == {"webgpu_switch": "2"}
    assert WebGLConfig("V", "R", WebGPUConfig()).to_api()["webgpu"]["webgpu_switch"] == "1"
    assert MediaDevicesConfig(1, 2, 3).to_api()["videoinput_num"] == "2"
    assert MacAddressConfig("computer").to_api() == {"model": "0"}
    assert MacAddressConfig("custom", "aa:bb").to_api()["address"] == "aa:bb"
    assert BrowserKernelConfig("chrome", "141").to_api()["version"] == "141"
    assert RandomUserAgentConfig(("140", "141"), ("Windows",)).to_api() == {
        "ua_version": ["140", "141"],
        "ua_system_version": ["Windows"],
    }
    assert PlatformAccount("example.com", "u", "p", "f").to_api()["fakey"] == "f"


def test_full_fingerprint_serialization() -> None:
    config = FingerprintConfig(
        automatic_timezone=False,
        timezone="UTC",
        location_by_ip=True,
        longitude=1.5,
        latitude=2.5,
        accuracy=100,
        location_permission="allow",
        language_by_ip=False,
        languages=("en-US", "en"),
        page_language_matches=True,
        page_language="en-US",
        user_agent="UA",
        screen_resolution="1920_1080",
        fonts=("Arial",),
        canvas_noise=True,
        webgl_mode="random",
        webgl_image_noise=False,
        flash="block",
        webrtc="proxy",
        audio_noise=True,
        do_not_track="true",
        hardware_concurrency="8",
        device_memory="8",
        port_scan_protection=True,
        allowed_scan_ports=("80", "443"),
        media_devices_mode="custom-noise",
        media_devices=MediaDevicesConfig(1, 1, 1),
        client_rects_noise=True,
        device_name_mode="custom",
        device_name="device",
        speech_replace=True,
        mac_address=MacAddressConfig("match"),
        gpu="on",
        browser_kernel=BrowserKernelConfig("chrome", "141"),
        random_user_agent=RandomUserAgentConfig(("141",)),
        tls_enabled=True,
        tls="TLS_AES_128_GCM_SHA256",
    )
    payload = config.to_api()
    assert payload["automatic_timezone"] == "0"
    assert payload["language"] == ["en-US", "en"]
    assert payload["scan_port_type"] == "1"
    assert payload["media_devices"] == "2"
    assert payload["device_name_switch"] == "2"
    assert payload["gpu"] == "1"
    assert "random_ua" not in payload

    random_payload = FingerprintConfig(
        random_user_agent=RandomUserAgentConfig(("141",)),
    ).to_api()
    assert random_payload["random_ua"] == {"ua_version": ["141"]}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"longitude": 181},
        {"latitude": -91},
        {"accuracy": 1},
        {"webgl_mode": "custom"},
        {"media_devices_mode": "custom-noise"},
        {"device_name_mode": "custom"},
        {"tls_enabled": True},
    ],
)
def test_fingerprint_conditional_validation(kwargs: dict[str, object]) -> None:
    with pytest.raises(AdsPowerValidationError):
        FingerprintConfig(**kwargs)  # type: ignore[arg-type]

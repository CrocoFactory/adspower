from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .._json import JsonObject
from ..errors import AdsPowerValidationError

BoolWire = Literal["0", "1"]


def _bool(value: bool) -> BoolWire:
    return "1" if value else "0"


@dataclass(frozen=True, slots=True)
class WebGPUConfig:
    mode: Literal["disabled", "webgl", "real"] = "webgl"

    def to_api(self) -> JsonObject:
        return {"webgpu_switch": {"disabled": "0", "webgl": "1", "real": "2"}[self.mode]}


@dataclass(frozen=True, slots=True)
class WebGLConfig:
    unmasked_vendor: str
    unmasked_renderer: str
    webgpu: WebGPUConfig | None = None

    def __post_init__(self) -> None:
        if not self.unmasked_vendor or not self.unmasked_renderer:
            raise AdsPowerValidationError("custom WebGL requires non-empty vendor and renderer")

    def to_api(self) -> JsonObject:
        value: JsonObject = {
            "unmasked_vendor": self.unmasked_vendor,
            "unmasked_renderer": self.unmasked_renderer,
        }
        if self.webgpu is not None:
            value["webgpu"] = self.webgpu.to_api()
        return value


@dataclass(frozen=True, slots=True)
class MediaDevicesConfig:
    audio_inputs: int
    video_inputs: int
    audio_outputs: int

    def __post_init__(self) -> None:
        if any(not 1 <= value <= 9 for value in (self.audio_inputs, self.video_inputs, self.audio_outputs)):
            raise AdsPowerValidationError("media device counts must be between 1 and 9")

    def to_api(self) -> JsonObject:
        return {
            "audioinput_num": str(self.audio_inputs),
            "videoinput_num": str(self.video_inputs),
            "audiooutput_num": str(self.audio_outputs),
        }


@dataclass(frozen=True, slots=True)
class MacAddressConfig:
    mode: Literal["computer", "match", "custom"]
    address: str | None = None

    def __post_init__(self) -> None:
        if self.mode == "custom" and not self.address:
            raise AdsPowerValidationError("custom MAC mode requires address")

    def to_api(self) -> JsonObject:
        result: JsonObject = {"model": {"computer": "0", "match": "1", "custom": "2"}[self.mode]}
        if self.address is not None:
            result["address"] = self.address
        return result


_CHROME_KERNELS = frozenset(
    (
        "92 99 102 105 108 111 114 115 116 117 118 119 120 121 122 123 124 125 "
        "126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 ua_auto"
    ).split()
)
_FIREFOX_KERNELS = frozenset(
    "100 107 114 120 123 126 129 132 135 138 141 144 ua_auto".split()
)


@dataclass(frozen=True, slots=True)
class BrowserKernelConfig:
    kernel_type: Literal["chrome", "firefox"]
    version: str = "ua_auto"

    def __post_init__(self) -> None:
        supported = _CHROME_KERNELS if self.kernel_type == "chrome" else _FIREFOX_KERNELS
        if self.version not in supported:
            raise AdsPowerValidationError(f"unsupported {self.kernel_type} kernel version: {self.version}")

    def to_api(self) -> JsonObject:
        return {"type": self.kernel_type, "version": self.version}


@dataclass(frozen=True, slots=True)
class RandomUserAgentConfig:
    versions: tuple[str, ...] = ()
    system_versions: tuple[str, ...] = ()

    def to_api(self) -> JsonObject:
        result: JsonObject = {}
        if self.versions:
            result["ua_version"] = list(self.versions)
        if self.system_versions:
            result["ua_system_version"] = list(self.system_versions)
        return result


ProxySoft = Literal[
    "brightdata",
    "brightauto",
    "oxylabsauto",
    "922S5auto",
    "ipfoxyauto",
    "922S5auth",
    "kookauto",
    "ssh",
    "other",
    "no_proxy",
]


@dataclass(frozen=True, slots=True)
class InlineProxyConfig:
    proxy_soft: ProxySoft
    proxy_type: Literal["http", "https", "socks5", "no_proxy"] | None = None
    host: str | None = None
    port: int | str | None = None
    user: str | None = None
    password: str | None = None
    proxy_url: str | None = None
    global_config: bool | None = None

    @classmethod
    def no_proxy(cls) -> "InlineProxyConfig":
        return cls(proxy_soft="no_proxy")

    def __post_init__(self) -> None:
        if self.port is not None:
            try:
                port = int(self.port)
            except (TypeError, ValueError) as exc:
                raise AdsPowerValidationError("proxy port must be an integer") from exc
            if not 0 <= port <= 65536:
                raise AdsPowerValidationError("proxy port must be between 0 and 65536")

    def to_api(self) -> JsonObject:
        result: JsonObject = {"proxy_soft": self.proxy_soft}
        values = {
            "proxy_type": self.proxy_type,
            "proxy_host": self.host,
            "proxy_port": str(self.port) if self.port is not None else None,
            "proxy_user": self.user,
            "proxy_password": self.password,
            "proxy_url": self.proxy_url,
            "global_config": _bool(self.global_config) if self.global_config is not None else None,
        }
        result.update({key: value for key, value in values.items() if value is not None})
        return result


@dataclass(frozen=True, slots=True)
class PlatformAccount:
    domain_name: str
    login_user: str
    password: str | None = None
    fakey: str | None = None

    def __post_init__(self) -> None:
        if not self.domain_name or not self.login_user:
            raise AdsPowerValidationError("platform account requires domain_name and login_user")

    def to_api(self) -> JsonObject:
        result: JsonObject = {"domain_name": self.domain_name, "login_user": self.login_user}
        if self.password is not None:
            result["password"] = self.password
        if self.fakey is not None:
            result["fakey"] = self.fakey
        return result


@dataclass(frozen=True, slots=True)
class FingerprintConfig:
    automatic_timezone: bool | None = None
    timezone: str | None = None
    location_by_ip: bool | None = None
    longitude: float | None = None
    latitude: float | None = None
    accuracy: int | None = None
    location_permission: Literal["ask", "allow", "block"] | None = None
    language_by_ip: bool | None = None
    languages: tuple[str, ...] = ()
    page_language_matches: bool | None = None
    page_language: str | None = None
    user_agent: str | None = None
    screen_resolution: str | None = None
    fonts: tuple[str, ...] = ()
    canvas_noise: bool | None = None
    webgl_mode: Literal["computer", "custom", "random"] | None = None
    webgl_image_noise: bool | None = None
    webgl: WebGLConfig | None = None
    flash: Literal["block", "allow"] | None = None
    webrtc: Literal["disabled", "forward", "proxy", "local"] | None = None
    audio_noise: bool | None = None
    do_not_track: Literal["default", "true", "false"] | None = None
    hardware_concurrency: Literal["default", "2", "4", "6", "8", "16", "32"] | None = None
    device_memory: Literal["default", "2", "4", "6", "8"] | None = None
    port_scan_protection: bool | None = None
    allowed_scan_ports: tuple[str, ...] = ()
    media_devices_mode: Literal["off", "local-noise", "custom-noise"] | None = None
    media_devices: MediaDevicesConfig | None = None
    client_rects_noise: bool | None = None
    device_name_mode: Literal["off", "mask", "custom"] | None = None
    device_name: str | None = None
    speech_replace: bool | None = None
    mac_address: MacAddressConfig | None = None
    gpu: Literal["local", "on", "off"] | None = None
    browser_kernel: BrowserKernelConfig | None = None
    random_user_agent: RandomUserAgentConfig | None = None
    tls_enabled: bool | None = None
    tls: str | None = None

    def __post_init__(self) -> None:
        if self.longitude is not None and not -180 <= self.longitude <= 180:
            raise AdsPowerValidationError("longitude must be between -180 and 180")
        if self.latitude is not None and not -90 <= self.latitude <= 90:
            raise AdsPowerValidationError("latitude must be between -90 and 90")
        if self.accuracy is not None and not 10 <= self.accuracy <= 5000:
            raise AdsPowerValidationError("accuracy must be between 10 and 5000")
        if self.webgl_mode == "custom" and self.webgl is None:
            raise AdsPowerValidationError("custom WebGL mode requires webgl config")
        if self.media_devices_mode == "custom-noise" and self.media_devices is None:
            raise AdsPowerValidationError("custom media devices mode requires counts")
        if self.device_name_mode == "custom" and not self.device_name:
            raise AdsPowerValidationError("custom device name mode requires device_name")
        if self.tls_enabled and not self.tls:
            raise AdsPowerValidationError("tls_enabled requires tls cipher list")
        if self.tls_enabled and self.browser_kernel is not None and self.browser_kernel.kernel_type != "chrome":
            raise AdsPowerValidationError("custom TLS is supported only with the Chrome kernel")

    def to_api(self) -> JsonObject:
        result: JsonObject = {}
        scalar = {
            "automatic_timezone": _bool(self.automatic_timezone) if self.automatic_timezone is not None else None,
            "timezone": self.timezone,
            "location_switch": _bool(self.location_by_ip) if self.location_by_ip is not None else None,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "accuracy": self.accuracy,
            "location": self.location_permission,
            "language_switch": _bool(self.language_by_ip) if self.language_by_ip is not None else None,
            "page_language_switch": _bool(self.page_language_matches)
            if self.page_language_matches is not None
            else None,
            "page_language": self.page_language,
            "ua": self.user_agent,
            "screen_resolution": self.screen_resolution,
            "canvas": _bool(self.canvas_noise) if self.canvas_noise is not None else None,
            "webgl_image": _bool(self.webgl_image_noise) if self.webgl_image_noise is not None else None,
            "flash": self.flash,
            "webrtc": self.webrtc,
            "audio": _bool(self.audio_noise) if self.audio_noise is not None else None,
            "do_not_track": self.do_not_track,
            "hardware_concurrency": self.hardware_concurrency,
            "device_memory": self.device_memory,
            "scan_port_type": _bool(self.port_scan_protection) if self.port_scan_protection is not None else None,
            "client_rects": _bool(self.client_rects_noise) if self.client_rects_noise is not None else None,
            "device_name": self.device_name,
            "speech_switch": _bool(self.speech_replace) if self.speech_replace is not None else None,
            "tls_switch": _bool(self.tls_enabled) if self.tls_enabled is not None else None,
            "tls": self.tls,
        }
        result.update({key: value for key, value in scalar.items() if value is not None})
        if self.languages:
            result["language"] = list(self.languages)
        if self.fonts:
            result["fonts"] = list(self.fonts)
        if self.allowed_scan_ports:
            result["allow_scan_ports"] = list(self.allowed_scan_ports)
        if self.webgl_mode is not None:
            result["webgl"] = {"computer": "0", "custom": "2", "random": "3"}[self.webgl_mode]
        if self.webgl is not None:
            result["webgl_config"] = self.webgl.to_api()
        if self.media_devices_mode is not None:
            result["media_devices"] = {"off": "0", "local-noise": "1", "custom-noise": "2"}[self.media_devices_mode]
        if self.media_devices is not None:
            result["media_devices_num"] = self.media_devices.to_api()
        if self.device_name_mode is not None:
            result["device_name_switch"] = {"off": "0", "mask": "1", "custom": "2"}[self.device_name_mode]
        if self.mac_address is not None:
            result["mac_address_config"] = self.mac_address.to_api()
        if self.gpu is not None:
            result["gpu"] = {"local": "0", "on": "1", "off": "2"}[self.gpu]
        if self.browser_kernel is not None:
            result["browser_kernel_config"] = self.browser_kernel.to_api()
        if self.random_user_agent is not None and self.user_agent is None:
            result["random_ua"] = self.random_user_agent.to_api()
        return result


class ScreenResolution:
    @staticmethod
    def fixed(width: int, height: int) -> str:
        if width <= 0 or height <= 0:
            raise ValueError("Screen dimensions must be positive")
        return f"{width}_{height}"

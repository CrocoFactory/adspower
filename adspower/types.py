from __future__ import annotations

from typing import Any, Literal

from typing_extensions import NotRequired, TypedDict

ProfileProxyType = Literal["http", "https", "socks5"]
StoredProxyType = Literal["http", "https", "socks5", "ssh"]
WebRtcType = str
LocationType = Literal["ask", "allow", "block"]
FlashType = Literal["allow", "block"]
DeviceNameType = str
MediaDeviceType = str
GPUType = str
WebGLVersion = str
AdsPowerBool = Literal[0, 1, "0", "1"]
CacheType = Literal["local_storage", "indexeddb", "extension_cache", "cookie", "history", "image_file"]
DoNotTrack = str
HardwareConcurrency = str
DeviceMemory = str


class ProxyConfig(TypedDict, total=False):
    """Typed fields for an inline AdsPower profile proxy configuration."""

    proxy_soft: str
    proxy_type: ProfileProxyType | str
    proxy_host: str
    proxy_port: int | str
    proxy_user: str
    proxy_password: str


class WebGLConfig(TypedDict):
    """WebGL fingerprint configuration."""

    unmasked_vendor: str
    unmasked_renderer: str
    webgpu: NotRequired[dict[str, Any]]


class MediaDeviceConfig(TypedDict):
    """Media-device count fingerprint configuration."""

    audioinput_num: str
    videoinput_num: str
    audiooutput_num: str


class RandomUserAgent(TypedDict, total=False):
    """Random user-agent version constraints."""

    ua_version: list[str]
    ua_system_version: list[str]


class MacAddressConfig(TypedDict):
    """MAC-address fingerprint configuration."""

    model: str
    address: NotRequired[str]


class BrowserKernelConfig(TypedDict):
    """Browser-kernel fingerprint configuration."""

    version: str
    type: str


class FingerprintConfig(TypedDict):
    """Known AdsPower fingerprint fields while preserving forward-compatible string values."""

    automatic_timezone: NotRequired[AdsPowerBool]
    timezone: NotRequired[str]
    webrtc: NotRequired[WebRtcType]
    location: NotRequired[LocationType]
    location_switch: NotRequired[AdsPowerBool]
    longitude: NotRequired[float]
    latitude: NotRequired[float]
    accuracy: NotRequired[int]
    language: NotRequired[list[str]]
    language_switch: NotRequired[AdsPowerBool]
    page_language_switch: NotRequired[AdsPowerBool]
    page_language: NotRequired[str]
    ua: NotRequired[str]
    screen_resolution: NotRequired[str]
    fonts: NotRequired[list[str]]
    canvas: NotRequired[AdsPowerBool]
    webgl_image: NotRequired[AdsPowerBool]
    webgl: NotRequired[WebGLVersion]
    webgl_config: NotRequired[WebGLConfig]
    audio: NotRequired[AdsPowerBool]
    do_not_track: NotRequired[DoNotTrack]
    hardware_concurrency: NotRequired[HardwareConcurrency]
    device_memory: NotRequired[DeviceMemory]
    flash: NotRequired[AdsPowerBool | FlashType]
    scan_port_type: NotRequired[AdsPowerBool]
    allow_scan_ports: NotRequired[list[str]]
    media_devices: NotRequired[MediaDeviceType]
    media_devices_num: NotRequired[MediaDeviceConfig]
    client_rects: NotRequired[AdsPowerBool]
    device_name_switch: NotRequired[DeviceNameType]
    device_name: NotRequired[str]
    random_ua: NotRequired[RandomUserAgent]
    speech_switch: NotRequired[AdsPowerBool]
    mac_address_config: NotRequired[MacAddressConfig]
    browser_kernel_config: NotRequired[BrowserKernelConfig]
    gpu: NotRequired[GPUType]
    tls_switch: NotRequired[AdsPowerBool]
    tls: NotRequired[str]

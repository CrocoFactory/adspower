from __future__ import annotations

from typing import Any, Literal

from typing_extensions import NotRequired, TypedDict

ProxySoft = str
ProfileProxyType = Literal["http", "https", "socks5"]
StoredProxyType = Literal["http", "https", "socks5", "ssh"]
ProxyType = ProfileProxyType
WebRtcType = Literal['forward', 'proxy', 'local', 'disabled', 'disableUDP'] | str
LocationType = Literal['ask', 'allow', 'block']
FlashType = Literal['allow', 'block']
DeviceNameType = Literal['0', '1', '2'] | str
MediaDeviceType = Literal['0', '1', '2'] | str
GPUType = Literal['0', '1', '2'] | str
WebGLVersion = Literal['0', '2', '3'] | str
AdsPowerBool = Literal[0, 1, "0", "1"]
IntBool = AdsPowerBool
CacheType = Literal["local_storage", "indexeddb", "extension_cache", "cookie", "history", "image_file"]
DoNotTrack = Literal["default", "true", "false"] | str
HardwareConcurrency = Literal["default", "2", "4", "6", "8", "16", "32"] | str
DeviceMemory = Literal["default", "2", "4", "6", "8"] | str


class ProxyConfig(TypedDict, total=False):
    soft: ProxySoft
    proxy_soft: str
    type: ProfileProxyType | str
    proxy_type: str
    host: str
    proxy_host: str
    port: int
    proxy_port: int | str
    user: str
    proxy_user: str
    password: str
    proxy_password: str


class WebGLConfig(TypedDict):
    unmasked_vendor: str
    unmasked_renderer: str
    webgpu: NotRequired[dict[str, Any]]


class MediaDeviceConfig(TypedDict):
    audioinput_num: str
    videoinput_num: str
    audiooutput_num: str


class RandomUserAgent(TypedDict, total=False):
    ua_version: list[str]
    ua_system_version: list[str]


class MacAddressConfig(TypedDict):
    model: Literal['0', '1', '2'] | str
    address: NotRequired[str]


class BrowserKernelConfig(TypedDict):
    version: str
    type: Literal["chrome", "firefox"] | str


class FingerprintConfig(TypedDict):
    automatic_timezone: NotRequired[IntBool]
    timezone: NotRequired[str]
    webrtc: NotRequired[WebRtcType]
    location: NotRequired[LocationType]
    location_switch: NotRequired[IntBool]
    longitude: NotRequired[float]
    latitude: NotRequired[float]
    accuracy: NotRequired[int]
    language: NotRequired[list[str]]
    language_switch: NotRequired[IntBool]
    page_language_switch: NotRequired[IntBool]
    page_language: NotRequired[str]
    ua: NotRequired[str]
    screen_resolution: NotRequired[str]
    fonts: NotRequired[list[str]]
    canvas: NotRequired[IntBool]
    webgl_image: NotRequired[IntBool]
    webgl: NotRequired[WebGLVersion]
    webgl_config: NotRequired[WebGLConfig]
    audio: NotRequired[IntBool]
    do_not_track: NotRequired[DoNotTrack]
    hardware_concurrency: NotRequired[HardwareConcurrency]
    device_memory: NotRequired[DeviceMemory]
    flash: NotRequired[IntBool | FlashType]
    scan_port_type: NotRequired[IntBool]
    allow_scan_ports: NotRequired[list[str]]
    media_devices: NotRequired[MediaDeviceType]
    media_devices_num: NotRequired[MediaDeviceConfig]
    client_rects: NotRequired[IntBool]
    device_name_switch: NotRequired[DeviceNameType]
    device_name: NotRequired[str]
    random_ua: NotRequired[RandomUserAgent]
    speech_switch: NotRequired[IntBool]
    mac_address_config: NotRequired[MacAddressConfig]
    browser_kernel_config: NotRequired[BrowserKernelConfig]
    gpu: NotRequired[GPUType]
    tls_switch: NotRequired[AdsPowerBool]
    tls: NotRequired[str]

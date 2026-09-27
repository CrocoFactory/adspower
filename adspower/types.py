from __future__ import annotations

from typing import Any, Literal

from typing_extensions import NotRequired, TypedDict

ProxySoft = str
ProxyType = Literal['http', 'https', 'socks5']
WebRtcType = Literal['forward', 'proxy', 'local', 'disabled']
LocationType = Literal['ask', 'allow', 'block']
FlashType = Literal['allow', 'block']
DeviceNameType = Literal[0, 1, 2]
MediaDeviceType = Literal[0, 1, 2]
GPUType = Literal[0, 1, 2]
WebGLVersion = Literal[0, 2, 3]
IntBool = Literal[0, 1]


class ProxyConfig(TypedDict, total=False):
    soft: ProxySoft
    proxy_soft: str
    type: ProxyType | str
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
    webgpu: dict[str, Any]


class MediaDeviceConfig(TypedDict):
    audioinput_num: int
    videoinput_num: int
    audiooutput_num: int


class RandomUserAgent(TypedDict):
    ua_browser: list[str]
    ua_version: list[int]
    ua_system_version: list[str]


class MacAddressConfig(TypedDict):
    model: int
    address: str


class BrowserKernelConfig(TypedDict):
    version: str
    type: str


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
    do_not_track: NotRequired[IntBool]
    hardware_concurrency: NotRequired[int]
    device_memory: NotRequired[int]
    flash: NotRequired[IntBool | FlashType]
    scan_port_type: NotRequired[IntBool]
    allow_scan_ports: NotRequired[list[int]]
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

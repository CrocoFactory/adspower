from typing import TypedDict, Literal, Optional, Any, Callable

HandlingTuple = tuple[dict[str, dict | str], Callable[[dict[str, Any]], Any] | Callable[[], Any]]

ProxySoft = Literal['luminati', 'lumauto', 'oxylabsatuto', '922S5', 'ipideaauto', 'ipfoxyauto', 'ssh', 'other',
                    'no_proxy']
IpChecker = Literal['ip2location', 'ipapi']
RepeatConfigType = Literal[0, 2, 3, 4]
ProxyType = Literal['http', 'https', 'socks5']
WebRtcType = Literal['forward', 'proxy', 'local', 'disabled']
LocationType = Literal['ask', 'allow', 'block']
FlashType = Literal['allow', 'block']
DeviceNameType = Literal[0, 1, 2]
MediaDeviceType = Literal[0, 1, 2]
GPUType = Literal[0, 1, 2]
WebGLVersion = Literal[0, 2, 3]
Cookies = list[dict[str, Any]] | dict[str, Any]
IntBool = Literal[0, 1]

UserSortKey = Literal['serial_number', 'last_open_time', 'created_time']
UserSortValue = Literal['desc', 'asc']
UserSort = dict[UserSortKey, UserSortValue]


class ProxyConfig(TypedDict):
    soft: ProxySoft
    type: ProxyType
    host: str
    port: int
    user: str
    password: str


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
    automatic_timezone: Optional[IntBool]
    timezone: Optional[str]
    webrtc: Optional[WebRtcType]
    location: Optional[LocationType]
    location_switch: Optional[IntBool]
    longitude: Optional[float]
    latitude: Optional[float]
    accuracy: Optional[int]
    language: Optional[list[str]]
    language_switch: Optional[IntBool]
    page_language_switch: Optional[IntBool]
    page_language: Optional[str]
    ua: Optional[str]
    screen_resolution: Optional[str]
    fonts: Optional[list[str]]
    canvas: Optional[IntBool]
    webgl_image: Optional[IntBool]
    webgl: Optional[WebGLVersion]
    webgl_config: Optional[WebGLConfig]
    audio: Optional[IntBool]
    do_not_track: Optional[IntBool]
    hardware_concurrency: Optional[int]
    device_memory: Optional[int]
    flash: Optional[IntBool | FlashType]
    scan_port_type: Optional[IntBool]
    allow_scan_ports: Optional[list[int]]
    media_devices: Optional[MediaDeviceType]
    media_devices_num: Optional[MediaDeviceConfig]
    client_rects: Optional[IntBool]
    device_name_switch: Optional[DeviceNameType]
    device_name: Optional[str]
    random_ua: Optional[RandomUserAgent]
    speech_switch: Optional[IntBool]
    mac_address_config: Optional[MacAddressConfig]
    browser_kernel_config: Optional[BrowserKernelConfig]
    gpu: Optional[GPUType]


class DebugInterface(TypedDict):
    selenium: str
    puppeteer: str


class BrowserResponse(TypedDict):
    ws: DebugInterface
    debug_port: str
    webdriver: str


class GroupInfo(TypedDict):
    group_id: int
    group_name: str
    remark: str


class CategoryInfo(TypedDict):
    id: int
    name: str
    remark: str


class ProfileInfo(TypedDict):
    profile_id: str
    serial_number: int
    name: str
    group_id: int
    group_name: str
    domain_name: str
    username: str
    remark: str
    created_time: int
    category_id: int
    ip: str
    ip_country: str
    ip_checker: str
    fakey: str
    password: str

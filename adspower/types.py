from typing import TypedDict, Literal, NotRequired, Any, Callable

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

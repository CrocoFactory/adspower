from typing import TypedDict, Literal, NotRequired

ProxySoft = Literal['luminati', 'lumauto', 'oxylabsatuto', '922S5', 'ipideaauto',
                    'ipfoxyauto', 'ssh', 'other', 'no_proxy']

ProxyType = Literal['http', 'https', 'socks5']


class UserProxyConfig(TypedDict):
    proxy_soft: ProxySoft
    proxy_type: ProxyType
    proxy_host: str
    proxy_port: int
    proxy_user: str
    proxy_password: str


class UpdatingProxyParams(TypedDict):
    profile_id: NotRequired[str]
    proxy_config: UserProxyConfig


class FingerprintConfig(TypedDict):
    ua: str
    language_switch: NotRequired[bool]


class CreateProfileParams(TypedDict):
    name: NotRequired[str]
    group_id: int
    user_proxy_config: NotRequired[UserProxyConfig]
    fingerprint_config: NotRequired[FingerprintConfig]


class QueryGroupParams(TypedDict):
    group_name: NotRequired[str]
    profile_id: NotRequired[str]
    page_size: NotRequired[int]


class QueryProfilesParams(TypedDict):
    group_id: NotRequired[int]
    page_size: NotRequired[int]


class GroupInfo(TypedDict):
    group_id: int
    group_name: str


class ProfileInfo(TypedDict):
    serial_number: int
    user_id: str
    name: str
    group_id: int
    group_name: str
    domain_name: str
    username: str
    remark: str
    created_time: int
    ip: str
    ip_country: str
    password: str
    last_open_time: int


GroupResponse = list[GroupInfo] | GroupInfo
ProfileResponse = list[ProfileInfo]

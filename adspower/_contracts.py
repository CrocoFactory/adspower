from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

HttpMethod = Literal["GET", "POST"]


@dataclass(frozen=True, slots=True)
class Endpoint:
    method: HttpMethod
    path: str


STATUS = Endpoint("GET", "/status")
CATEGORY_LIST = Endpoint("GET", "/api/v2/category/list")
PROFILE_START = Endpoint("POST", "/api/v2/browser-profile/start")
PROFILE_STOP = Endpoint("POST", "/api/v2/browser-profile/stop")
PROFILE_CREATE = Endpoint("POST", "/api/v2/browser-profile/create")
PROFILE_UPDATE = Endpoint("POST", "/api/v2/browser-profile/update")
PROFILE_DELETE = Endpoint("POST", "/api/v2/browser-profile/delete")
PROFILE_LIST = Endpoint("POST", "/api/v2/browser-profile/list")
PROFILE_LOCAL_ACTIVE = Endpoint("GET", "/api/v1/browser/local-active")
PROFILE_MOVE = Endpoint("POST", "/api/v1/user/regroup")
PROFILE_COOKIES = Endpoint("GET", "/api/v2/browser-profile/cookies")
PROFILE_UA = Endpoint("POST", "/api/v2/browser-profile/ua")
PROFILE_STOP_ALL = Endpoint("POST", "/api/v2/browser-profile/stop-all")
PROFILE_NEW_FINGERPRINT = Endpoint("POST", "/api/v2/browser-profile/new-fingerprint")
PROFILE_DELETE_CACHE = Endpoint("POST", "/api/v2/browser-profile/delete-cache")
PROFILE_SHARE = Endpoint("POST", "/api/v2/browser-profile/share")
PROFILE_ACTIVE = Endpoint("GET", "/api/v2/browser-profile/active")
PROFILE_CLOUD_ACTIVE = Endpoint("POST", "/api/v1/browser/cloud-active")
GROUP_CREATE = Endpoint("POST", "/api/v1/group/create")
GROUP_UPDATE = Endpoint("POST", "/api/v1/group/update")
GROUP_LIST = Endpoint("GET", "/api/v1/group/list")
PROXY_CREATE = Endpoint("POST", "/api/v2/proxy-list/create")
PROXY_UPDATE = Endpoint("POST", "/api/v2/proxy-list/update")
PROXY_LIST = Endpoint("POST", "/api/v2/proxy-list/list")
PROXY_DELETE = Endpoint("POST", "/api/v2/proxy-list/delete")
TAG_LIST = Endpoint("POST", "/api/v2/browser-tags/list")
TAG_CREATE = Endpoint("POST", "/api/v2/browser-tags/create")
TAG_UPDATE = Endpoint("POST", "/api/v2/browser-tags/update")
TAG_DELETE = Endpoint("POST", "/api/v2/browser-tags/delete")
KERNEL_DOWNLOAD = Endpoint("POST", "/api/v2/browser-profile/download-kernel")
KERNEL_LIST = Endpoint("GET", "/api/v2/browser-profile/kernels")
APP_UPDATE_PATCH = Endpoint("POST", "/api/v2/browser-profile/update-patch")

ALL_ENDPOINTS = (
    STATUS, CATEGORY_LIST, PROFILE_START, PROFILE_STOP, PROFILE_CREATE, PROFILE_UPDATE,
    PROFILE_DELETE, PROFILE_LIST, PROFILE_LOCAL_ACTIVE, PROFILE_MOVE, PROFILE_COOKIES,
    PROFILE_UA, PROFILE_STOP_ALL, PROFILE_NEW_FINGERPRINT, PROFILE_DELETE_CACHE,
    PROFILE_SHARE, PROFILE_ACTIVE, PROFILE_CLOUD_ACTIVE, GROUP_CREATE, GROUP_UPDATE,
    GROUP_LIST, PROXY_CREATE, PROXY_UPDATE, PROXY_LIST, PROXY_DELETE, TAG_LIST,
    TAG_CREATE, TAG_UPDATE, TAG_DELETE, KERNEL_DOWNLOAD, KERNEL_LIST, APP_UPDATE_PATCH,
)

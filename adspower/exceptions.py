from typing import Any
from adspower.types import UpdatingProxyParams


class NoParamsFound(Exception):
    """Raised when params are not specified via positional arguments or keyword arguments"""
    def __init__(self):
        super().__init__("Params are not specified via positional arguments or keyword arguments")


class ZeroResponse(Exception):
    """Raised if response is 0"""
    def __init__(self, message: str, request: dict[str, Any], response: dict[str]):
        super().__init__(f"{message}. \nRequest: {request}. \nResponse: {response}")


class ProxyUpdateError(ZeroResponse):
    """Raised when proxy update is failed"""
    def __init__(self, request: dict[str, Any], response: dict[str]):
        super().__init__("The proxy update is failed", request, response)


class UserAgentUpdateError(ZeroResponse):
    """Raised when user agent update is failed"""
    def __init__(self, request: dict[str, Any], response: dict[str]):
        super().__init__("The user agent update is failed", request, response)


class ProfileCreationError(ZeroResponse):
    """Raised when profile creation is failed"""
    def __init__(self, request: dict[str, Any], response: dict[str]):
        super().__init__("The profile creation is failed", request, response)


class GroupQueryError(ZeroResponse):
    """Raised when group query is failed"""
    def __init__(self, request: dict[str, Any], response: dict[str]):
        super().__init__("The group query is failed", request, response)


class ProfileQueryError(ZeroResponse):
    """Raised when profile query is failed"""
    def __init__(self, request: dict[str, Any], response: dict[str]):
        super().__init__("The profile query is failed", request, response)


class ProfileNotFound(ZeroResponse):
    """Raised when profile getting or deleting is failed"""
    def __init__(self, request: dict[str, Any], response: dict[str]):
        super().__init__("Profile getting is failed", request, response)


class QuittingProfileError(ZeroResponse):
    """Raised when quitting profile is failed."""
    def __init__(self, request: dict[str, Any], response: dict[str]):
        super().__init__("Quitting profile is failed. Profile can be already closed", request, response)


class NoGroupIdFound(Exception):
    """Raised when group id is not specified"""
    def __init__(self):
        super().__init__("The id of a group isn't passed")


class NoProfileIdFound(Exception):
    """Raised when profile id is not specified"""
    def __init__(self):
        super().__init__("The id of a profile isn't passed")


class NoUserAgentFound(Exception):
    """Raised when user agent is not specified"""
    def __init__(self):
        super().__init__("The user agent isn't passed")


class InvalidProxyConfig(Exception):
    """Raised when proxy config is invalid"""

    def __init__(self, proxy_config: dict[str] | UpdatingProxyParams):
        super().__init__(f"The proxy config is invalid. Config: {proxy_config}")


class ExceededQPS(Exception):
    """Raised when amount of queries per second is exceeded"""
    def __init__(self):
        super().__init__("Too many request per second, please try later")


class UnavailableAPI(Exception):
    """Raised when API url specified with invalid port or AdsPower is not opened"""
    def __init__(self, port: int):
        super().__init__(f"Your API url is specified with invalid port or AdsPower is not opened. You provided port {port}")

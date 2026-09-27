from __future__ import annotations

from typing import Any

from httpx import ConnectError, Request, RequestError

from adspower.types import ProxyConfig


class AdsPowerError(Exception):
    """Base class for all errors raised by the modern client."""


class AdsPowerConnectionError(AdsPowerError):
    pass


class AdsPowerTimeoutError(AdsPowerError):
    pass


class AdsPowerAPIError(AdsPowerError):
    def __init__(
        self,
        message: str,
        *,
        code: int | str | None = None,
        response: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.response = response


class ProfileNotFoundError(AdsPowerAPIError):
    pass


class AuthenticationError(AdsPowerAPIError):
    pass


class RateLimitError(AdsPowerAPIError):
    pass


class ZeroResponseError(RequestError):
    """Raised if response code is 0"""

    def __init__(self, message: str, request: Request, response: dict[str, Any]):
        super().__init__(f"{message}. Response: {response}", request=request)
        self.__response = response

    @property
    def response(self) -> dict[str, Any]:
        return self.__response


class ExceededQPSError(ConnectionRefusedError):
    """Raised when amount of queries per second is exceeded"""

    def __init__(self):
        super().__init__("Too many request per second, please try later")


class InternalAPIError(RequestError):
    """Raised when an internal API error is encountered"""

    def __init__(self, request: Request, response: dict[str, Any]):
        super().__init__(f'The internal API error is encountered. Response: {response}', request=request)
        self.__response = response

    @property
    def response(self) -> dict[str, Any]:
        return self.__response


class UnavailableAPIError(ConnectError):
    """Raised when API url specified with invalid port or AdsPower is not opened"""

    def __init__(self, port: int):
        super().__init__(f"API url is specified with invalid port or AdsPower is not opened. Port is {port}")
        self.__port = port

    @property
    def port(self) -> Any:
        return self.__port


class APIRefusedError(ConnectionRefusedError):
    """Raised when user have no paid subscription to use API"""

    def __init__(self):
        super().__init__("Local API is only available in paid subscriptions")


class InvalidPortError(TypeError):
    """Raised when port is not represented as an integer between 1 and 65535"""

    def __init__(self, port: Any):
        super().__init__(f"Port must be a number between 1 and 65535. You provided port {port}")
        self.__port = port

    @property
    def port(self) -> Any:
        return self.__port


class InvalidProxyConfig(Exception):
    """Raised when proxy config is invalid"""

    def __init__(self, proxy_config: ProxyConfig):
        super().__init__(f"The proxy config is invalid. Config: {proxy_config}")

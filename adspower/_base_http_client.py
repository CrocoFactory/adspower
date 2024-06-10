import time
from abc import ABC, abstractmethod
from typing import Any, Optional, Callable, ClassVar, Union
from httpx import USE_CLIENT_DEFAULT, Response
from httpx._client import UseClientDefault
from httpx._types import (URLTypes, RequestContent, RequestData, RequestFiles, QueryParamTypes, HeaderTypes,
                          CookieTypes,
                          AuthTypes, TimeoutTypes, RequestExtensions)
from adspower.exceptions import InvalidPortError, InternalAPIError, ExceededQPSError, APIRefusedError, ZeroResponseError


class _BaseHTTPClient(ABC):
    _request_availability = 0
    _delay: ClassVar[float] = 0.9
    _timeout = 5.0

    def __init__(self, port: int = 50325):
        self._port = port
        self._api_url = f'http://local.adspower.net:{self._port}'

    @property
    def api_url(self) -> str:
        return self._api_url

    @staticmethod
    def _validate_response(response: Response, error_msg: str) -> None:
        response.raise_for_status()
        request = response.request
        response_json = response.json()

        if response_json.get('message'):
            raise InternalAPIError(request=request, response=response_json)

        if response_json['code'] != 0:
            if 'Too many request per second, please check' in response_json['msg']:
                raise ExceededQPSError
            elif 'This feature is only available in paid subscriptions' in response_json['msg']:
                raise APIRefusedError
            else:
                raise ZeroResponseError(error_msg, request, response_json)

    @classmethod
    def set_delay(cls, value: float) -> None:
        """
        Sets the delay between requests
        :param value: Delay in seconds
        :return: None
        """
        if isinstance(value, Union[float, int]):
            cls._delay = value
        else:
            raise TypeError('Delay must be a float')

    @classmethod
    def set_timeout(cls, value: float) -> None:
        """
        Sets the timeout of the request
        :param value: Timeout in seconds
        :return: None
        """
        if isinstance(value, Union[float, int]):
            cls._timeout = value
        else:
            raise TypeError('Timeout must be a float')

    @classmethod
    def set_port(cls, value: int) -> None:
        """
        Sets the port of the client. Use it only when your Local API has non-default port.
        :param value: Port to be set
        :return: None
        """
        if 1 <= value <= 65535:
            cls._port = value
            cls._api_url = f'http://local.adspower.net:{value}'
        else:
            raise InvalidPortError(value)

    @classmethod
    def available(cls) -> bool:
        """
        Checks if the client is available.
        :return: True if client is not locked due to delay, False otherwise
        """
        current_time = time.time()
        return cls._request_availability < current_time

    @staticmethod
    @abstractmethod
    def _delay_request(func: Callable) -> Callable:
        pass

    @staticmethod
    @abstractmethod
    def _handle_request(func: Callable) -> Callable:
        pass

    @property
    def port(self) -> int:
        return self._port

    @_handle_request
    @_delay_request
    @abstractmethod
    def post(
            self,
            url: URLTypes,
            *,
            error_msg: str,
            content: Optional[RequestContent] = None,
            data: Optional[RequestData] = None,
            files: Optional[RequestFiles] = None,
            json: Optional[Any] = None,
            params: Optional[QueryParamTypes] = None,
            headers: Optional[HeaderTypes] = None,
            cookies: Optional[CookieTypes] = None,
            auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
            follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
            timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
            extensions: Optional[RequestExtensions] = None,
    ) -> Response:
        pass

    @_handle_request
    @_delay_request
    @abstractmethod
    def get(
            self,
            url: URLTypes,
            *,
            error_msg: str,
            params: QueryParamTypes | None = None,
            headers: HeaderTypes | None = None,
            cookies: CookieTypes | None = None,
            auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
            follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
            timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
            extensions: RequestExtensions | None = None,
    ) -> Response:
        pass

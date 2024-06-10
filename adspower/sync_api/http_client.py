import time
from functools import wraps
from typing import Any, Optional, Callable
from httpx import Client, USE_CLIENT_DEFAULT, Response, ConnectError, InvalidURL
from httpx._client import UseClientDefault
from httpx._types import (URLTypes, RequestContent, RequestData, RequestFiles, QueryParamTypes, HeaderTypes,
                          CookieTypes,
                          AuthTypes, TimeoutTypes, RequestExtensions)
from urllib3.exceptions import MaxRetryError, NewConnectionError
from adspower.exceptions import UnavailableAPIError
from adspower._base_http_client import _BaseHTTPClient


class HTTPClient(Client, _BaseHTTPClient):

    def __init__(self):
        """
        HTTPClient is a wrapper around httpx's Client to make it easier to perform requests against Local API.
        You can customize internal behaviour of the package using HTTPClient`s methods, such as `set_timeout`, `set_port`,
        `set_delay` and get information about client availability using `available`
        """
        port = 50325
        _BaseHTTPClient.__init__(self, port)
        Client.__init__(self, base_url=self._api_url, timeout=self._timeout)

    @staticmethod
    def _delay_request(func: Callable[..., Response]):

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_time = time.time()

            if _BaseHTTPClient.available():
                result = func(*args, **kwargs)
                _BaseHTTPClient._request_availability = time.time() + HTTPClient._delay
            else:
                time.sleep(HTTPClient._request_availability - current_time)
                _BaseHTTPClient._request_availability = time.time() + HTTPClient._delay
                result = func(*args, **kwargs)

            return result

        return wrapper

    @staticmethod
    def _handle_request(func: Callable[..., Response]):
        @wraps(func)
        def wrapper(
                self: "HTTPClient",
                *args,
                **kwargs,
        ) -> Response:
            try:
                super().get('/status')
            except (MaxRetryError, ConnectError, NewConnectionError, ConnectionRefusedError, InvalidURL):
                raise UnavailableAPIError(self._port)
            else:
                response = func(self, *args, **kwargs)
                HTTPClient._validate_response(response, kwargs['error_msg'])

            return response

        return wrapper

    @_handle_request
    @_delay_request
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
        return super().post(
            url=url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions
        )

    @_handle_request
    @_delay_request
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
        return super().get(
            url=url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions
        )

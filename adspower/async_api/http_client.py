import asyncio
import time
from functools import wraps
from typing import Any, Optional, Callable, Awaitable
from httpx import AsyncClient, USE_CLIENT_DEFAULT, Response, ConnectError, InvalidURL
from httpx._client import UseClientDefault
from httpx._types import (URLTypes, RequestContent, RequestData, RequestFiles, QueryParamTypes, HeaderTypes,
                          CookieTypes,
                          AuthTypes, TimeoutTypes, RequestExtensions)
from urllib3.exceptions import MaxRetryError, NewConnectionError
from adspower.exceptions import UnavailableAPIError
from adspower._base_http_client import _BaseHTTPClient


class HTTPClient(AsyncClient, _BaseHTTPClient):
    def __init__(self):
        """
        HTTPClient is a wrapper around httpx's AsyncClient to make it easier to perform requests against Local API.
        You can customize internal behaviour of the package using HTTPClient`s methods, such as `set_timeout`, `set_port`,
        `set_delay` and get information about client availability using `available`
        """
        port = 50325
        _BaseHTTPClient.__init__(self, port)
        AsyncClient.__init__(self, base_url=self._api_url, timeout=self._timeout)

    @staticmethod
    def _delay_request(func: Callable[..., Awaitable[Response]]):
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            current_time = time.time()

            if _BaseHTTPClient.available():
                result = await func(*args, **kwargs)
                _BaseHTTPClient._request_availability = time.time() + HTTPClient._delay
            else:
                await asyncio.sleep(HTTPClient._request_availability - current_time)
                _BaseHTTPClient._request_availability = time.time() + HTTPClient._delay
                result = await func(*args, **kwargs)

            return result

        return wrapper

    @staticmethod
    def _handle_request(func: Callable[..., Awaitable[Response]]):
        @wraps(func)
        async def wrapper(
                self: "HTTPClient",
                *args,
                **kwargs,
        ) -> Response:
            try:
                await super().get('/status')
            except (MaxRetryError, ConnectError, NewConnectionError, ConnectionRefusedError, InvalidURL):
                raise UnavailableAPIError(self.__port)
            else:
                response = await func(self, *args, **kwargs)
                HTTPClient._validate_response(response, kwargs['error_msg'])
            return response

        return wrapper

    @_handle_request
    @_delay_request
    async def post(
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
        return await super().post(
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
    async def get(
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
        return await super().get(
            url=url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions
        )

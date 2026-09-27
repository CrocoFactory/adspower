from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from adspower._base_http_client import _BaseHTTPClient
from adspower.exceptions import UnavailableAPIError


class HTTPClient(httpx.AsyncClient, _BaseHTTPClient):
    """Deprecated 2.x async HTTP client. Prefer ``AsyncAdsPowerClient``."""

    def __init__(self) -> None:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else None
        super().__init__(base_url=self._base_url, timeout=self._timeout, headers=headers)
        self._last_request = 0.0

    async def _request_legacy(self, method: str, url: Any, *, error_msg: str, **kwargs: Any) -> httpx.Response:
        wait = self._delay - (time.monotonic() - self._last_request)
        if wait > 0:
            await asyncio.sleep(wait)
        kwargs = {key: value for key, value in kwargs.items() if value is not None}
        try:
            response = await super().request(method, url, **kwargs)
        except (httpx.ConnectError, httpx.InvalidURL) as exc:
            raise UnavailableAPIError(self.port) from exc
        self._last_request = time.monotonic()
        self._validate_response(response, error_msg)
        return response

    async def post(self, url: Any, *, error_msg: str, **kwargs: Any) -> httpx.Response:
        return await self._request_legacy("POST", url, error_msg=error_msg, **kwargs)

    async def get(self, url: Any, *, error_msg: str, **kwargs: Any) -> httpx.Response:
        return await self._request_legacy("GET", url, error_msg=error_msg, **kwargs)

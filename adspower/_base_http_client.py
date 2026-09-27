from __future__ import annotations

import os
from typing import ClassVar

from httpx import Response

from adspower.exceptions import APIRefusedError, ExceededQPSError, InternalAPIError, InvalidPortError, ZeroResponseError


class _BaseHTTPClient:
    """Compatibility settings used by the deprecated 2.x HTTP clients."""

    _delay: ClassVar[float] = 0.0
    _timeout: ClassVar[float] = 30.0
    _base_url: ClassVar[str] = os.getenv("ADSPOWER_BASE_URL", "http://127.0.0.1:50325").rstrip("/")
    _api_key: ClassVar[str | None] = os.getenv("ADSPOWER_API_KEY")

    @staticmethod
    def _validate_response(response: Response, error_msg: str) -> None:
        response.raise_for_status()
        payload = response.json()
        if payload.get("message"):
            raise InternalAPIError(request=response.request, response=payload)
        if payload.get("code") not in (0, "0", None):
            message = str(payload.get("msg", ""))
            if "Too many request" in message:
                raise ExceededQPSError
            if "paid subscriptions" in message:
                raise APIRefusedError
            raise ZeroResponseError(error_msg, response.request, payload)

    @classmethod
    def set_delay(cls, value: float) -> None:
        if not isinstance(value, (float, int)):
            raise TypeError("Delay must be numeric")
        cls._delay = float(value)

    @classmethod
    def set_timeout(cls, value: float) -> None:
        if not isinstance(value, (float, int)):
            raise TypeError("Timeout must be numeric")
        cls._timeout = float(value)

    @classmethod
    def set_port(cls, value: int) -> None:
        if not isinstance(value, int) or not 1 <= value <= 65535:
            raise InvalidPortError(value)
        cls._base_url = f"http://127.0.0.1:{value}"

    @classmethod
    def set_base_url(cls, value: str) -> None:
        cls._base_url = value.rstrip("/")

    @classmethod
    def set_api_key(cls, value: str | None) -> None:
        cls._api_key = value

    @classmethod
    def available(cls) -> bool:
        return True

    @property
    def api_url(self) -> str:
        return self._base_url

    @property
    def port(self) -> int:
        from urllib.parse import urlsplit

        return urlsplit(str(self.base_url)).port or 80

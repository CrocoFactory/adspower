from __future__ import annotations

from typing import Any


class AdsPowerError(Exception):
    """Base class for all errors raised by the modern client."""


class AdsPowerValidationError(AdsPowerError, ValueError):
    """Raised when a request violates a documented client-side constraint."""


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
        method: str | None = None,
        path: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.response = response
        self.method = method
        self.path = path


class ProfileNotFoundError(AdsPowerAPIError):
    pass


class AuthenticationError(AdsPowerAPIError):
    pass


class RateLimitError(AdsPowerAPIError):
    pass

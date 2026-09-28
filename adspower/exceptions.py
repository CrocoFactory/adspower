from __future__ import annotations

from typing import Any


class AdsPowerError(Exception):
    """Base class for errors raised at an AdsPower SDK boundary."""


class AdsPowerValidationError(AdsPowerError, ValueError):
    """Raised when an argument violates a documented SDK or Local API constraint."""


class AdsPowerConfigurationError(AdsPowerError, ValueError):
    """Raised when client configuration is invalid or internally inconsistent."""


class AdsPowerTransportError(AdsPowerError):
    """Base class for HTTP transport failures before a valid API response exists."""

    def __init__(self, message: str, *, method: str | None = None, path: str | None = None) -> None:
        super().__init__(message)
        self.method = method
        self.path = path


class AdsPowerConnectionError(AdsPowerTransportError):
    """Raised when HTTPX cannot complete an AdsPower request."""


class AdsPowerTimeoutError(AdsPowerTransportError):
    """Raised when an AdsPower request exceeds its configured timeout."""


class AdsPowerAPIError(AdsPowerError):
    """Raised when AdsPower returns an HTTP or business-level API error."""

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


class AdsPowerResponseError(AdsPowerAPIError):
    """Raised when a successful response violates the expected Local API contract."""


class ProfileNotFoundError(AdsPowerAPIError):
    """Raised when a valid profile query returns no matching profile."""


class AuthenticationError(AdsPowerAPIError):
    """Raised when AdsPower rejects Local API credentials."""


class RateLimitError(AdsPowerAPIError):
    """Raised when AdsPower rejects a request because of a server-side rate limit."""

    def __init__(self, message: str, *, retry_after: float | None = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


AdsPowerAuthenticationError = AuthenticationError
AdsPowerRateLimitError = RateLimitError

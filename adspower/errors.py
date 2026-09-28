from __future__ import annotations

class AdsPowerError(Exception):
    """Base class for failures raised by the AdsPower SDK."""


class AdsPowerValidationError(AdsPowerError, ValueError):
    """Invalid caller input at a public AdsPower operation boundary."""


class AdsPowerConfigurationError(AdsPowerError, ValueError):
    """Invalid SDK or networking configuration."""


class AdsPowerTransportError(AdsPowerError):
    """No valid AdsPower HTTP response was obtained."""

    def __init__(self, message: str, *, method: str | None = None, path: str | None = None) -> None:
        super().__init__(message)
        self.method = method
        self.path = path


class AdsPowerConnectionError(AdsPowerTransportError):
    """Connection, DNS, socket, or other HTTP transport failure."""


class AdsPowerTimeoutError(AdsPowerTransportError):
    """Request timeout."""


class AdsPowerAPIError(AdsPowerError):
    """AdsPower rejected a request through HTTP or its business envelope."""

    def __init__(
        self,
        message: str,
        *,
        method: str | None = None,
        path: str | None = None,
        status: int | None = None,
        code: int | None = None,
        server_message: str | None = None,
    ) -> None:
        super().__init__(message)
        self.method = method
        self.path = path
        self.status = status
        self.code = code
        self.server_message = server_message


class AdsPowerAuthenticationError(AdsPowerAPIError):
    """AdsPower rejected credentials using a reliable authentication signal."""


class AdsPowerRateLimitError(AdsPowerAPIError):
    """AdsPower rejected a request because of a reliable rate-limit signal."""

    def __init__(self, message: str, *, retry_after: float | None = None, **kwargs: object) -> None:
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.retry_after = retry_after


class AdsPowerProtocolError(AdsPowerError):
    """A response was received but violated the expected Local API protocol."""

    def __init__(self, message: str, *, method: str | None = None, path: str | None = None) -> None:
        super().__init__(message)
        self.method = method
        self.path = path


class AdsPowerNotFoundError(AdsPowerError, LookupError):
    """A successful SDK convenience lookup did not find the requested object."""

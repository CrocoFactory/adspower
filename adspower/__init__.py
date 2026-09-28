"""Modern sync and async clients for the AdsPower Local API."""

from .async_client import AsyncAdsPowerClient, AsyncBrowserSession
from .client import AdsPowerClient, BrowserSession
from .config import BrowserEndpointPolicy, ClientConfig
from .exceptions import (
    AdsPowerAPIError,
    AdsPowerAuthenticationError,
    AdsPowerConfigurationError,
    AdsPowerConnectionError,
    AdsPowerError,
    AdsPowerRateLimitError,
    AdsPowerResponseError,
    AdsPowerTimeoutError,
    AdsPowerTransportError,
    AdsPowerValidationError,
    AuthenticationError,
    ProfileNotFoundError,
    RateLimitError,
)
from .models import (
    BrowserConnection,
    BrowserStatus,
    Category,
    Group,
    Profile,
    ProfileSelector,
    Proxy,
    ProxySoftware,
    RunningBrowser,
    ScreenResolution,
)
from .rate_limit import AdsPowerRatePolicy, RateLimit
from .types import AdsPowerBool, CacheType, FingerprintConfig, ProfileProxyType, ProxyConfig, StoredProxyType

__version__ = "3.0.0"

__all__ = [
    "AdsPowerAPIError",
    "AdsPowerAuthenticationError",
    "AdsPowerClient",
    "AdsPowerConfigurationError",
    "AdsPowerConnectionError",
    "AdsPowerError",
    "AdsPowerRateLimitError",
    "AdsPowerRatePolicy",
    "AdsPowerResponseError",
    "AdsPowerTimeoutError",
    "AdsPowerTransportError",
    "AdsPowerValidationError",
    "AsyncAdsPowerClient",
    "AsyncBrowserSession",
    "AuthenticationError",
    "BrowserConnection",
    "BrowserEndpointPolicy",
    "BrowserSession",
    "BrowserStatus",
    "CacheType",
    "Category",
    "ClientConfig",
    "FingerprintConfig",
    "Group",
    "Profile",
    "ProfileNotFoundError",
    "ProfileProxyType",
    "ProfileSelector",
    "Proxy",
    "ProxyConfig",
    "ProxySoftware",
    "RateLimit",
    "RateLimitError",
    "RunningBrowser",
    "ScreenResolution",
    "StoredProxyType",
    "AdsPowerBool",
]

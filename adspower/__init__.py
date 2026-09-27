"""Modern sync and async clients for the AdsPower Local API."""

from .async_client import AsyncAdsPowerClient, AsyncBrowserSession
from .client import AdsPowerClient, BrowserSession
from .config import ClientConfig
from .exceptions import AdsPowerValidationError
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
from .rate_limit import RateLimit
from .types import AdsPowerBool, CacheType, FingerprintConfig, ProfileProxyType, ProxyConfig, StoredProxyType

__version__ = "3.0.0"

__all__ = [
    "AdsPowerClient",
    "AsyncAdsPowerClient",
    "AsyncBrowserSession",
    "BrowserConnection",
    "BrowserStatus",
    "BrowserSession",
    "ClientConfig",
    "Category",
    "AdsPowerBool",
    "AdsPowerValidationError",
    "FingerprintConfig",
    "Group",
    "Profile",
    "ProfileSelector",
    "ProfileProxyType",
    "Proxy",
    "ProxyConfig",
    "ProxySoftware",
    "RateLimit",
    "ScreenResolution",
    "StoredProxyType",
    "RunningBrowser",
]

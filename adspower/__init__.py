"""Modern sync and async clients for the AdsPower Local API."""

from .async_client import AsyncAdsPowerClient, AsyncBrowserSession
from .client import AdsPowerClient, BrowserSession
from .config import ClientConfig
from .models import BrowserConnection, Group, Profile, ProxySoftware, ScreenResolution
from .rate_limit import RateLimit
from .types import FingerprintConfig, ProxyConfig

__version__ = "3.0.0"

__all__ = [
    "AdsPowerClient",
    "AsyncAdsPowerClient",
    "AsyncBrowserSession",
    "BrowserConnection",
    "BrowserSession",
    "ClientConfig",
    "FingerprintConfig",
    "Group",
    "Profile",
    "ProxyConfig",
    "ProxySoftware",
    "RateLimit",
    "ScreenResolution",
]

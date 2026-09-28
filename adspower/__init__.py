"""Typed sync and async clients for the AdsPower Local API."""

from importlib.metadata import PackageNotFoundError, version

from .async_client import AsyncAdsPowerClient
from .client import AdsPowerClient
from .config import AdsPowerConfig, BrowserEndpointPolicy
from .errors import (
    AdsPowerAPIError,
    AdsPowerAuthenticationError,
    AdsPowerConfigurationError,
    AdsPowerConnectionError,
    AdsPowerError,
    AdsPowerNotFoundError,
    AdsPowerProtocolError,
    AdsPowerRateLimitError,
    AdsPowerTimeoutError,
    AdsPowerTransportError,
    AdsPowerValidationError,
)
from .models import (
    BrowserConnection,
    BrowserKernelConfig,
    BrowserStatus,
    BrowserTag,
    Category,
    CloudBrowserStatus,
    CreatedProfile,
    FingerprintConfig,
    Group,
    InlineProxyConfig,
    KernelInfo,
    MacAddressConfig,
    MediaDevicesConfig,
    Page,
    PlatformAccount,
    Profile,
    Proxy,
    RandomUserAgentConfig,
    RunningBrowser,
    ScreenResolution,
    WebGLConfig,
    WebGPUConfig,
)
from .models.proxies import StoredProxyConfig
from .rate_limit import AdsPowerRatePolicy, RateLimit
from .resources import AsyncBrowserSession, BrowserSession, TagCreate, TagUpdate

try:
    __version__ = version("adspower")
except PackageNotFoundError:
    __version__ = "3.0.0"

__all__ = [
    "AdsPowerAPIError",
    "AdsPowerAuthenticationError",
    "AdsPowerClient",
    "AdsPowerConfig",
    "AdsPowerConfigurationError",
    "AdsPowerConnectionError",
    "AdsPowerError",
    "AdsPowerNotFoundError",
    "AdsPowerProtocolError",
    "AdsPowerRateLimitError",
    "AdsPowerRatePolicy",
    "AdsPowerTimeoutError",
    "AdsPowerTransportError",
    "AdsPowerValidationError",
    "AsyncAdsPowerClient",
    "AsyncBrowserSession",
    "BrowserConnection",
    "BrowserEndpointPolicy",
    "BrowserKernelConfig",
    "BrowserSession",
    "BrowserStatus",
    "BrowserTag",
    "Category",
    "CloudBrowserStatus",
    "CreatedProfile",
    "FingerprintConfig",
    "Group",
    "InlineProxyConfig",
    "KernelInfo",
    "MacAddressConfig",
    "MediaDevicesConfig",
    "Page",
    "PlatformAccount",
    "Profile",
    "Proxy",
    "RandomUserAgentConfig",
    "RateLimit",
    "RunningBrowser",
    "ScreenResolution",
    "StoredProxyConfig",
    "TagCreate",
    "TagUpdate",
    "WebGLConfig",
    "WebGPUConfig",
    "__version__",
]

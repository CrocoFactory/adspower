from __future__ import annotations

import re
from dataclasses import replace
from typing import Callable
from urllib.parse import urlsplit, urlunsplit

import httpx

from ..config import AdsPowerConfig
from ..errors import AdsPowerConfigurationError, AdsPowerProtocolError
from ..models import BrowserConnection


def _format_host(host: str) -> str:
    return f"[{host}]" if ":" in host and not host.startswith("[") else host


def _loopback(host: str | None) -> bool:
    return host in {"127.0.0.1", "localhost", "::1"}


def _rewrite_authority(endpoint: str, target_host: str) -> str:
    parsed = urlsplit(endpoint if "://" in endpoint else f"//{endpoint}")
    if not parsed.hostname:
        raise AdsPowerProtocolError(f"malformed browser endpoint: {endpoint!r}")
    if not _loopback(parsed.hostname):
        return endpoint
    port = f":{parsed.port}" if parsed.port is not None else ""
    authority = f"{_format_host(target_host)}{port}"
    if "://" not in endpoint:
        return authority
    return urlunsplit((parsed.scheme, authority, parsed.path, parsed.query, parsed.fragment))


def resolve_browser_connection(connection: BrowserConnection, config: AdsPowerConfig) -> BrowserConnection:
    """Resolve topology separately from response parsing."""
    api_host = urlsplit(config.base_url).hostname
    if not api_host:
        raise AdsPowerConfigurationError("base_url has no host")
    target = config.browser_host or api_host
    selenium = connection.raw_selenium_debugger_address
    playwright = connection.raw_playwright_cdp_url
    marionette_host = connection.marionette_host

    if selenium is None and connection.debug_port is not None:
        selenium = f"{_format_host(target)}:{connection.debug_port}"
    elif (
        selenium is not None
        and config.browser_endpoint_policy == "rewrite_loopback_to_api_host"
        and not _loopback(target)
    ):
        selenium = _rewrite_authority(selenium, target)

    if (
        playwright is not None
        and config.browser_endpoint_policy == "rewrite_loopback_to_api_host"
        and not _loopback(target)
    ):
        playwright = _rewrite_authority(playwright, target)

    if marionette_host is None and connection.marionette_port is not None and not _loopback(target):
        marionette_host = target

    return replace(
        connection,
        selenium_debugger_address=selenium,
        playwright_cdp_url=playwright,
        marionette_host=marionette_host,
    )


def remote_chromium_version(
    debugger_address: str,
    *,
    timeout: float = 2.0,
    get: Callable[[str, float], object] | None = None,
) -> str:
    """Probe /json/version without ever forwarding the AdsPower API token."""
    parsed = urlsplit(debugger_address if "://" in debugger_address else f"//{debugger_address}")
    if not parsed.hostname or parsed.port is None:
        raise AdsPowerConfigurationError("invalid Selenium debugger address")
    host = _format_host(parsed.hostname)
    url = urlunsplit(("http", f"{host}:{parsed.port}", "/json/version", "", ""))
    try:
        if get is None:
            with httpx.Client(follow_redirects=False, timeout=timeout, headers={}) as client:
                response = client.get(url)
                response.raise_for_status()
                payload = response.json()
        else:
            payload = get(url, timeout)
    except Exception as exc:
        raise AdsPowerConfigurationError(
            f"could not query remote Chromium version at {url}; pass a matching Selenium service"
        ) from exc
    if not isinstance(payload, dict):
        raise AdsPowerProtocolError("browser /json/version response must be an object")
    browser = payload.get("Browser")
    if not isinstance(browser, str):
        raise AdsPowerProtocolError("browser /json/version response is missing Browser")
    match = re.search(r"(?:Chrome|Chromium)/([0-9]+(?:\.[0-9]+)*)", browser)
    if match is None:
        raise AdsPowerProtocolError("browser /json/version response has no Chromium version")
    return match.group(1).split(".", 1)[0]

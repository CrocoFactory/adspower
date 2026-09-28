from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from types import TracebackType
from typing import Any, Awaitable, Callable, Literal
from urllib.parse import urlsplit, urlunsplit
from urllib.request import urlopen

from .models import BrowserConnection


def _remote_chromium_version(debugger_address: str) -> str:
    """Read the running remote Chromium version for Selenium Manager."""
    parsed = urlsplit(debugger_address if "://" in debugger_address else f"//{debugger_address}")
    if not parsed.hostname or not parsed.port:
        raise RuntimeError(f"Invalid remote AdsPower Selenium debugger address: {debugger_address!r}")
    host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    version_url = urlunsplit(("http", f"{host}:{parsed.port}", "/json/version", "", ""))
    try:
        with urlopen(version_url, timeout=2) as response:  # noqa: S310 - host comes from the user's AdsPower config
            payload = json.load(response)
    except Exception as exc:
        raise RuntimeError(
            "Could not query the remote AdsPower browser version at "
            f"{version_url}; pass a matching Selenium service explicitly"
        ) from exc
    browser = payload.get("Browser") if isinstance(payload, Mapping) else None
    match = re.search(r"(?:Chrome|Chromium)/([0-9]+(?:\.[0-9]+)*)", str(browser or ""))
    if not match:
        raise RuntimeError(
            "The remote AdsPower /json/version response did not contain a Chromium version; "
            "pass a matching Selenium service explicitly"
        )
    return match.group(1).split(".", 1)[0]


def _is_loopback_debugger(debugger_address: str) -> bool:
    parsed = urlsplit(debugger_address if "://" in debugger_address else f"//{debugger_address}")
    return parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def _is_loopback_host(host: str | None) -> bool:
    return host in {"127.0.0.1", "localhost", "::1"}


def _playwright_connect_kwargs(
    *,
    timeout: float | None = None,
    slow_mo: float | None = None,
    headers: Mapping[str, str] | None = None,
    is_local: bool | None = None,
    no_defaults: bool | None = None,
    artifacts_dir: str | None = None,
    connect_kwargs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    typed = {"timeout": timeout, "slow_mo": slow_mo, "headers": headers, "is_local": is_local, "no_defaults": no_defaults, "artifacts_dir": artifacts_dir}
    extra = dict(connect_kwargs or {})
    collisions = [key for key, value in typed.items() if value is not None and key in extra]
    if collisions:
        raise ValueError(f"Duplicate Playwright connection options: {', '.join(collisions)}")
    return {**{key: value for key, value in typed.items() if value is not None}, **extra}


class SeleniumSession(AbstractContextManager[Any]):
    def __init__(self, connection: BrowserConnection, *, stop: Callable[[], None], stop_on_exit: bool = True, page_load_strategy: Literal["normal", "eager", "none"] | None = None, options: Any = None, browser: Literal["auto", "chromium", "chrome", "firefox"] = "auto", service: Any = None, service_kwargs: Mapping[str, Any] | None = None, webdriver_kwargs: Mapping[str, Any] | None = None) -> None:
        self.connection, self._stop = connection, stop
        self.stop_on_exit = stop_on_exit
        self.page_load_strategy = page_load_strategy
        self.options = options
        # Firefox attachment is experimental and must be selected explicitly;
        # a synthetic or stale marionette_port must not change the default.
        self.browser = "chromium" if browser in ("auto", "chrome") else browser
        self.service = service
        self.service_kwargs = dict(service_kwargs or {})
        self.webdriver_kwargs = dict(webdriver_kwargs or {})
        self.driver: Any = None
        self._closed = False

    def __enter__(self) -> Any:
        try:
            if "service" in self.webdriver_kwargs or "options" in self.webdriver_kwargs:
                raise ValueError("webdriver_kwargs cannot contain service or options")
            if self.service is not None and self.service_kwargs:
                raise ValueError("service and service_kwargs are mutually exclusive")
            if self.browser not in {"chromium", "firefox"}:
                raise ValueError("browser must be auto, chromium, chrome, or firefox")
            try:
                if self.browser == "firefox":
                    from selenium.webdriver.firefox.options import Options  # pyright: ignore[reportMissingImports]
                    from selenium.webdriver.firefox.service import Service  # pyright: ignore[reportMissingImports]
                    from selenium.webdriver.firefox.webdriver import WebDriver  # pyright: ignore[reportMissingImports]
                else:
                    from selenium.webdriver.chrome.options import Options  # pyright: ignore[reportMissingImports]
                    from selenium.webdriver.chrome.service import Service  # pyright: ignore[reportMissingImports]
                    from selenium.webdriver.chrome.webdriver import WebDriver  # pyright: ignore[reportMissingImports]
            except ImportError as exc:
                raise ImportError("Install Selenium support with: pip install 'adspower[selenium]'") from exc
            options_class: Any = Options
            service_class: Any = Service
            webdriver_class: Any = WebDriver
            options: Any = self.options or options_class()
            if self.browser == "firefox" and not self.connection.marionette_port:
                raise RuntimeError("Firefox AdsPower attachment requires a marionette_port returned by the Local API")
            if self.browser == "chromium":
                if not self.connection.selenium_debugger_address:
                    raise RuntimeError("AdsPower did not return a Selenium debugger endpoint")
                existing = getattr(options, "_experimental_options", {}).get("debuggerAddress")
                if existing and existing != self.connection.selenium_debugger_address:
                    raise ValueError("Selenium options already contain a different debuggerAddress")
                if not existing:
                    options.add_experimental_option("debuggerAddress", self.connection.selenium_debugger_address)
            if self.page_load_strategy is not None:
                options.page_load_strategy = self.page_load_strategy
            if self.service is not None:
                service = self.service
            else:
                service_kwargs = dict(self.service_kwargs)
                if self.browser == "firefox":
                    args = list(service_kwargs.get("service_args", []))
                    if "--marionette-port" not in args:
                        args.extend(["--marionette-port", str(self.connection.marionette_port)])
                    if "--connect-existing" not in args:
                        args.append("--connect-existing")
                    if self.connection.marionette_host and not _is_loopback_host(self.connection.marionette_host) and "--marionette-host" not in args:
                        args.extend(["--marionette-host", self.connection.marionette_host])
                    service_kwargs["service_args"] = args
                local_driver_path = not self.connection.marionette_host or _is_loopback_host(self.connection.marionette_host)
                if self.connection.webdriver and local_driver_path and os.path.isfile(self.connection.webdriver) and "executable_path" not in service_kwargs:
                    service_kwargs["executable_path"] = self.connection.webdriver
                elif self.browser == "chromium" and self.connection.selenium_debugger_address and not _is_loopback_debugger(self.connection.selenium_debugger_address):
                    # A path such as /remote/adspower/chromedriver is commonly
                    # meaningful only inside the AdsPower container. Selenium Manager
                    # otherwise sees only the local machine and may choose a driver
                    # for a different locally installed Chrome.
                    options.browser_version = _remote_chromium_version(self.connection.selenium_debugger_address)
                service = service_class(**service_kwargs)
            self.driver = webdriver_class(service=service, options=options, **self.webdriver_kwargs)
            return self.driver
        except BaseException:
            self.close(preserve_error=True)
            raise

    def close(self, *, preserve_error: bool = False) -> None:
        if self._closed:
            return
        self._closed = True
        cleanup_error: Exception | None = None
        try:
            if self.driver is not None:
                self.driver.quit()
        except Exception as exc:
            cleanup_error = exc
        finally:
            self.driver = None
        if self.stop_on_exit:
            try:
                self._stop()
            except Exception as exc:
                cleanup_error = cleanup_error or exc
        if cleanup_error is not None and not preserve_error:
            raise cleanup_error

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None) -> bool:
        self.close(preserve_error=exc is not None)
        return False


class PlaywrightSession(AbstractContextManager[Any]):
    def __init__(self, connection: BrowserConnection, *, stop: Callable[[], None], stop_on_exit: bool = True, timeout: float | None = None, slow_mo: float | None = None, headers: Mapping[str, str] | None = None, is_local: bool | None = None, no_defaults: bool = True, artifacts_dir: str | None = None, connect_kwargs: Mapping[str, Any] | None = None) -> None:
        self.connection, self._stop = connection, stop
        self.stop_on_exit = stop_on_exit
        self._connect_options = {
            "timeout": timeout,
            "slow_mo": slow_mo,
            "headers": headers,
            "is_local": is_local,
            "no_defaults": no_defaults,
            "artifacts_dir": artifacts_dir,
            "connect_kwargs": connect_kwargs,
        }
        self._playwright: Any = None
        self.browser: Any = None
        self._closed = False

    def __enter__(self) -> Any:
        try:
            try:
                from playwright.sync_api import sync_playwright  # pyright: ignore[reportMissingImports]
            except ImportError as exc:
                raise ImportError("Install Playwright support with: pip install 'adspower[playwright]'") from exc
            if not self.connection.playwright_cdp_url:
                raise RuntimeError("AdsPower did not return a Playwright CDP endpoint")
            connect_kwargs = _playwright_connect_kwargs(**self._connect_options)
            self._playwright = sync_playwright().start()
            self.browser = self._playwright.chromium.connect_over_cdp(self.connection.playwright_cdp_url, **connect_kwargs)
            return self.browser
        except BaseException:
            self.close(preserve_error=True)
            raise

    def close(self, *, preserve_error: bool = False) -> None:
        if self._closed:
            return
        self._closed = True
        cleanup_error: Exception | None = None
        for cleanup in (lambda: self.browser.close() if self.browser is not None else None, self._stop if self.stop_on_exit else lambda: None, lambda: self._playwright.stop() if self._playwright is not None else None):
            try:
                cleanup()
            except Exception as exc:
                cleanup_error = cleanup_error or exc
        self.browser = None
        self._playwright = None
        if cleanup_error is not None and not preserve_error:
            raise cleanup_error

    def __exit__(self, exc_type: Any, exc: BaseException | None, traceback: Any) -> bool:
        self.close(preserve_error=exc is not None)
        return False


class AsyncPlaywrightSession(AbstractAsyncContextManager[Any]):
    def __init__(self, connection: BrowserConnection, *, stop: Callable[[], Awaitable[None]], stop_on_exit: bool = True, timeout: float | None = None, slow_mo: float | None = None, headers: Mapping[str, str] | None = None, is_local: bool | None = None, no_defaults: bool = True, artifacts_dir: str | None = None, connect_kwargs: Mapping[str, Any] | None = None) -> None:
        self.connection, self._stop = connection, stop
        self.stop_on_exit = stop_on_exit
        self._connect_options = {
            "timeout": timeout,
            "slow_mo": slow_mo,
            "headers": headers,
            "is_local": is_local,
            "no_defaults": no_defaults,
            "artifacts_dir": artifacts_dir,
            "connect_kwargs": connect_kwargs,
        }
        self._playwright: Any = None
        self.browser: Any = None
        self._closed = False

    async def __aenter__(self) -> Any:
        try:
            try:
                from playwright.async_api import async_playwright  # pyright: ignore[reportMissingImports]
            except ImportError as exc:
                raise ImportError("Install Playwright support with: pip install 'adspower[playwright]'") from exc
            if not self.connection.playwright_cdp_url:
                raise RuntimeError("AdsPower did not return a Playwright CDP endpoint")
            connect_kwargs = _playwright_connect_kwargs(**self._connect_options)
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.connect_over_cdp(self.connection.playwright_cdp_url, **connect_kwargs)
            return self.browser
        except BaseException:
            await self.close(preserve_error=True)
            raise

    async def close(self, *, preserve_error: bool = False) -> None:
        if self._closed:
            return
        self._closed = True
        cleanup_error: Exception | None = None
        cleanups: list[Callable[[], Awaitable[Any]]] = []
        if self.browser is not None:
            cleanups.append(self.browser.close)
        if self.stop_on_exit:
            cleanups.append(self._stop)
        if self._playwright is not None:
            cleanups.append(self._playwright.stop)
        for cleanup in cleanups:
            try:
                await cleanup()
            except Exception as exc:
                cleanup_error = cleanup_error or exc
        self.browser = None
        self._playwright = None
        if cleanup_error is not None and not preserve_error:
            raise cleanup_error

    async def __aexit__(self, exc_type: Any, exc: BaseException | None, traceback: Any) -> bool:
        await self.close(preserve_error=exc is not None)
        return False

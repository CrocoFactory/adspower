from __future__ import annotations

import os
from collections.abc import Mapping
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any, Literal

from ..errors import AdsPowerProtocolError, AdsPowerValidationError
from ..models import BrowserConnection
from .endpoints import remote_chromium_version


class SeleniumAdapter(AbstractContextManager[Any]):
    """Attach Selenium only; AdsPower process ownership stays with BrowserSession."""

    def __init__(
        self,
        connection: BrowserConnection,
        *,
        page_load_strategy: Literal["normal", "eager", "none"] | None = None,
        options: Any = None,
        browser: Literal["chromium", "firefox"] = "chromium",
        service: Any = None,
        service_kwargs: Mapping[str, Any] | None = None,
        webdriver_kwargs: Mapping[str, Any] | None = None,
        probe_timeout: float = 2.0,
    ) -> None:
        self.connection = connection
        self.page_load_strategy = page_load_strategy
        self.options = options
        self.browser = browser
        self.service = service
        self.service_kwargs = dict(service_kwargs or {})
        self.webdriver_kwargs = dict(webdriver_kwargs or {})
        self.probe_timeout = probe_timeout
        self.driver: Any = None
        self._closed = False

    def __enter__(self) -> Any:
        try:
            if "service" in self.webdriver_kwargs or "options" in self.webdriver_kwargs:
                raise AdsPowerValidationError("webdriver_kwargs cannot contain service or options")
            if self.service is not None and self.service_kwargs:
                raise AdsPowerValidationError("service and service_kwargs are mutually exclusive")
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

            options: Any = self.options or Options()
            if self.page_load_strategy is not None:
                options.page_load_strategy = self.page_load_strategy

            if self.browser == "firefox":
                if self.connection.marionette_port is None:
                    raise AdsPowerProtocolError("AdsPower did not return a Firefox marionette_port")
            else:
                address = self.connection.selenium_debugger_address
                if not address:
                    raise AdsPowerProtocolError("AdsPower did not return a Selenium debugger endpoint")
                existing = getattr(options, "_experimental_options", {}).get("debuggerAddress")
                if existing and existing != address:
                    raise AdsPowerValidationError("Selenium options contain a different debuggerAddress")
                if not existing:
                    options.add_experimental_option("debuggerAddress", address)

            if self.service is not None:
                service = self.service
            else:
                kwargs = dict(self.service_kwargs)
                if self.browser == "firefox":
                    args = list(kwargs.get("service_args", []))
                    args.extend(["--marionette-port", str(self.connection.marionette_port), "--connect-existing"])
                    if self.connection.marionette_host:
                        args.extend(["--marionette-host", self.connection.marionette_host])
                    kwargs["service_args"] = args
                elif self.connection.webdriver and os.path.isfile(self.connection.webdriver):
                    kwargs.setdefault("executable_path", self.connection.webdriver)
                elif self.connection.selenium_debugger_address:
                    from urllib.parse import urlsplit

                    parsed = urlsplit(
                        self.connection.selenium_debugger_address
                        if "://" in self.connection.selenium_debugger_address
                        else f"//{self.connection.selenium_debugger_address}"
                    )
                    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
                        options.browser_version = remote_chromium_version(
                            self.connection.selenium_debugger_address,
                            timeout=self.probe_timeout,
                        )
                service = Service(**kwargs)
            self.driver = WebDriver(  # pyright: ignore[reportArgumentType]
                service=service, options=options, **self.webdriver_kwargs
            )
            return self.driver
        except BaseException:
            self.close(preserve_error=True)
            raise

    def close(self, *, preserve_error: bool = False) -> None:
        if self._closed:
            return
        self._closed = True
        error: Exception | None = None
        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception as exc:
                error = exc
            finally:
                self.driver = None
        if error is not None and not preserve_error:
            raise error

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        self.close(preserve_error=exc is not None)
        return False

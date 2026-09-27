from __future__ import annotations

from contextlib import AbstractAsyncContextManager, AbstractContextManager
from types import TracebackType
from typing import Any, Awaitable, Callable, Literal

from .models import BrowserConnection


class SeleniumSession(AbstractContextManager[Any]):
    def __init__(
        self,
        connection: BrowserConnection,
        *,
        stop: Callable[[], None],
        stop_on_exit: bool = True,
        start_maximized: bool = False,
        page_load_strategy: Literal["normal", "eager", "none"] | None = None,
        options: Any = None,
    ) -> None:
        self.connection = connection
        self._stop = stop
        self.stop_on_exit = stop_on_exit
        self.start_maximized = start_maximized
        self.page_load_strategy = page_load_strategy
        self.options = options
        self.driver: Any = None
        self._closed = False

    def __enter__(self) -> Any:
        try:
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.webdriver import WebDriver
        except ImportError as exc:
            raise ImportError("Install Selenium support with: pip install 'adspower[selenium]'") from exc
        if not self.connection.selenium:
            raise RuntimeError("AdsPower did not return a Selenium debugger endpoint")
        options = self.options or Options()
        options.add_experimental_option("debuggerAddress", self.connection.selenium)
        if self.page_load_strategy is not None:
            options.page_load_strategy = self.page_load_strategy
        service = Service(executable_path=self.connection.webdriver) if self.connection.webdriver else Service()
        self.driver = WebDriver(service=service, options=options)
        if self.start_maximized:
            self.driver.maximize_window()
        return self.driver

    def close(self, *, preserve_error: bool = False) -> None:
        if self._closed:
            return
        self._closed = True
        cleanup_error: BaseException | None = None
        try:
            if self.driver is not None:
                self.driver.quit()
        except BaseException as exc:
            cleanup_error = exc
        finally:
            self.driver = None
        if self.stop_on_exit:
            try:
                self._stop()
            except BaseException as exc:
                cleanup_error = cleanup_error or exc
        if cleanup_error is not None and not preserve_error:
            raise cleanup_error

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        self.close(preserve_error=exc is not None)
        return False


class PlaywrightSession(AbstractContextManager[Any]):
    def __init__(self, connection: BrowserConnection, *, stop: Callable[[], None], stop_on_exit: bool = True) -> None:
        self.connection = connection
        self._stop = stop
        self.stop_on_exit = stop_on_exit
        self._playwright: Any = None
        self.browser: Any = None
        self._closed = False

    def __enter__(self) -> Any:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ImportError("Install Playwright support with: pip install 'adspower[playwright]'") from exc
        if not self.connection.playwright_cdp:
            raise RuntimeError("AdsPower did not return a Playwright CDP endpoint")
        self._playwright = sync_playwright().start()
        self.browser = self._playwright.chromium.connect_over_cdp(self.connection.playwright_cdp)
        return self.browser

    def close(self, *, preserve_error: bool = False) -> None:
        if self._closed:
            return
        self._closed = True
        cleanup_error: BaseException | None = None
        for cleanup in (
            lambda: self.browser.close() if self.browser is not None else None,
            self._stop if self.stop_on_exit else lambda: None,
            lambda: self._playwright.stop() if self._playwright is not None else None,
        ):
            try:
                cleanup()
            except BaseException as exc:
                cleanup_error = cleanup_error or exc
        self.browser = None
        self._playwright = None
        if cleanup_error is not None and not preserve_error:
            raise cleanup_error

    def __exit__(self, exc_type: Any, exc: BaseException | None, traceback: Any) -> bool:
        self.close(preserve_error=exc is not None)
        return False


class AsyncPlaywrightSession(AbstractAsyncContextManager[Any]):
    def __init__(
        self,
        connection: BrowserConnection,
        *,
        stop: Callable[[], Awaitable[None]],
        stop_on_exit: bool = True,
    ) -> None:
        self.connection = connection
        self._stop = stop
        self.stop_on_exit = stop_on_exit
        self._playwright: Any = None
        self.browser: Any = None
        self._closed = False

    async def __aenter__(self) -> Any:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise ImportError("Install Playwright support with: pip install 'adspower[playwright]'") from exc
        if not self.connection.playwright_cdp:
            raise RuntimeError("AdsPower did not return a Playwright CDP endpoint")
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.connect_over_cdp(self.connection.playwright_cdp)
        return self.browser

    async def close(self, *, preserve_error: bool = False) -> None:
        if self._closed:
            return
        self._closed = True
        cleanup_error: BaseException | None = None
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
            except BaseException as exc:
                cleanup_error = cleanup_error or exc
        self.browser = None
        self._playwright = None
        if cleanup_error is not None and not preserve_error:
            raise cleanup_error

    async def __aexit__(self, exc_type: Any, exc: BaseException | None, traceback: Any) -> bool:
        await self.close(preserve_error=exc is not None)
        return False

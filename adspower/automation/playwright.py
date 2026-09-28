from __future__ import annotations

from collections.abc import Mapping
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from typing import Any

from ..errors import AdsPowerProtocolError, AdsPowerValidationError
from ..models import BrowserConnection


def _connect_kwargs(
    *,
    timeout: float | None,
    slow_mo: float | None,
    headers: Mapping[str, str] | None,
    is_local: bool | None,
    no_defaults: bool | None,
    artifacts_dir: str | None,
    extra: Mapping[str, Any] | None,
) -> dict[str, Any]:
    values: dict[str, Any] = {
        "timeout": timeout,
        "slow_mo": slow_mo,
        "headers": headers,
        "is_local": is_local,
        "no_defaults": no_defaults,
        "artifacts_dir": artifacts_dir,
    }
    result = {key: value for key, value in values.items() if value is not None}
    extras = dict(extra or {})
    collisions = set(result).intersection(extras)
    if collisions:
        raise AdsPowerValidationError(f"duplicate Playwright connection options: {', '.join(sorted(collisions))}")
    result.update(extras)
    return result


class PlaywrightAdapter(AbstractContextManager[Any]):
    def __init__(
        self,
        connection: BrowserConnection,
        *,
        timeout: float | None = None,
        slow_mo: float | None = None,
        headers: Mapping[str, str] | None = None,
        is_local: bool | None = None,
        no_defaults: bool = True,
        artifacts_dir: str | None = None,
        connect_kwargs: Mapping[str, Any] | None = None,
    ) -> None:
        self.connection = connection
        self.kwargs = _connect_kwargs(
            timeout=timeout,
            slow_mo=slow_mo,
            headers=headers,
            is_local=is_local,
            no_defaults=no_defaults,
            artifacts_dir=artifacts_dir,
            extra=connect_kwargs,
        )
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
                raise AdsPowerProtocolError("AdsPower did not return a Playwright CDP endpoint")
            self._playwright = sync_playwright().start()
            self.browser = self._playwright.chromium.connect_over_cdp(self.connection.playwright_cdp_url, **self.kwargs)
            return self.browser
        except BaseException:
            self.close(preserve_error=True)
            raise

    def close(self, *, preserve_error: bool = False) -> None:
        if self._closed:
            return
        self._closed = True
        error: Exception | None = None
        for cleanup in (
            (lambda: self.browser.close()) if self.browser is not None else None,
            (lambda: self._playwright.stop()) if self._playwright is not None else None,
        ):
            if cleanup is None:
                continue
            try:
                cleanup()
            except Exception as exc:
                error = error or exc
        self.browser = None
        self._playwright = None
        if error is not None and not preserve_error:
            raise error

    def __exit__(self, exc_type: object, exc: BaseException | None, traceback: object) -> bool:
        self.close(preserve_error=exc is not None)
        return False


class AsyncPlaywrightAdapter(AbstractAsyncContextManager[Any]):
    def __init__(
        self,
        connection: BrowserConnection,
        *,
        timeout: float | None = None,
        slow_mo: float | None = None,
        headers: Mapping[str, str] | None = None,
        is_local: bool | None = None,
        no_defaults: bool = True,
        artifacts_dir: str | None = None,
        connect_kwargs: Mapping[str, Any] | None = None,
    ) -> None:
        self.connection = connection
        self.kwargs = _connect_kwargs(
            timeout=timeout,
            slow_mo=slow_mo,
            headers=headers,
            is_local=is_local,
            no_defaults=no_defaults,
            artifacts_dir=artifacts_dir,
            extra=connect_kwargs,
        )
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
                raise AdsPowerProtocolError("AdsPower did not return a Playwright CDP endpoint")
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.connect_over_cdp(
                self.connection.playwright_cdp_url, **self.kwargs
            )
            return self.browser
        except BaseException:
            await self.close(preserve_error=True)
            raise

    async def close(self, *, preserve_error: bool = False) -> None:
        if self._closed:
            return
        self._closed = True
        error: Exception | None = None
        cleanups = []
        if self.browser is not None:
            cleanups.append(self.browser.close)
        if self._playwright is not None:
            cleanups.append(self._playwright.stop)
        for cleanup in cleanups:
            try:
                await cleanup()
            except Exception as exc:
                error = error or exc
        self.browser = None
        self._playwright = None
        if error is not None and not preserve_error:
            raise error

    async def __aexit__(self, exc_type: object, exc: BaseException | None, traceback: object) -> bool:
        await self.close(preserve_error=exc is not None)
        return False

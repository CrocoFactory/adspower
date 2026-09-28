from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from types import TracebackType
from typing import Any, Literal

from .. import _contracts as c
from .._json import JsonValue, require_list, require_object
from ..automation import (
    AsyncPlaywrightAdapter,
    PlaywrightAdapter,
    SeleniumAdapter,
    resolve_browser_connection,
)
from ..config import AdsPowerConfig
from ..errors import AdsPowerValidationError
from ..models import BrowserConnection, BrowserStatus, CloudBrowserStatus, RunningBrowser
from ..models.browsers import (
    parse_browser_connection,
    parse_browser_status,
    parse_cloud_browser_status,
    parse_running_browser,
)
from ._common import (
    AsyncTransportProtocol,
    SyncTransportProtocol,
    bool_wire,
    id_list,
    response_data,
    selector,
)


def _launch_args(
    value: str | Sequence[str] | None,
    *,
    start_maximized: bool,
) -> str | list[JsonValue] | None:
    if value is None:
        args: list[str] = []
    elif isinstance(value, str):
        if not start_maximized:
            return value
        args = [value]
    else:
        if isinstance(value, (bytes, bytearray)):
            raise AdsPowerValidationError("launch_args must be a string or sequence of strings")
        args = [str(item) for item in value]
    if (
        start_maximized
        and "--start-maximized" not in args
        and not any(item.startswith("--window-size=") for item in args)
    ):
        args.append("--start-maximized")
    if not args:
        return None
    result: list[JsonValue] = []
    result.extend(args)
    return result


def build_start_payload(
    profile_id: str | None,
    profile_no: str | None,
    *,
    ip_tab: bool | None = None,
    launch_args: str | Sequence[str] | None = None,
    headless: bool | None = None,
    last_opened_tabs: bool | None = None,
    proxy_detection: bool | None = None,
    password_filling: bool | None = None,
    password_saving: bool | None = None,
    delete_cache: bool | None = None,
    cdp_mask: bool | None = None,
    device_scale: int | float | str | None = None,
    start_maximized: bool = False,
) -> dict[str, JsonValue]:
    payload = selector(profile_id, profile_no)
    args = _launch_args(launch_args, start_maximized=start_maximized)
    if args is not None:
        payload["launch_args"] = args
    for key, value in {
        "ip_tab": ip_tab,
        "headless": headless,
        "last_opened_tabs": last_opened_tabs,
        "proxy_detection": proxy_detection,
        "password_filling": password_filling,
        "password_saving": password_saving,
        "delete_cache": delete_cache,
        "cdp_mask": cdp_mask,
    }.items():
        if value is not None:
            payload[key] = bool_wire(value)
    if device_scale is not None:
        payload["device_scale"] = device_scale
    return payload


class BrowserSession(AbstractContextManager["BrowserSession"]):
    """Own one AdsPower browser process. Automation adapters only own attachment."""

    def __init__(
        self,
        *,
        profile_id: str | None,
        profile_no: str | None,
        connection: BrowserConnection,
        resource: "BrowsersResource",
    ) -> None:
        self.profile_id = profile_id
        self.profile_no = profile_no
        self.connection = connection
        self._resource = resource
        self._stopped = False

    def __enter__(self) -> "BrowserSession":
        return self

    def stop(self) -> None:
        if not self._stopped:
            self._resource.stop(self.profile_id, profile_no=self.profile_no)
            self._stopped = True

    def selenium(
        self,
        *,
        page_load_strategy: Literal["normal", "eager", "none"] | None = None,
        options: Any = None,
        browser: Literal["chromium", "firefox"] = "chromium",
        service: Any = None,
        service_kwargs: Mapping[str, Any] | None = None,
        webdriver_kwargs: Mapping[str, Any] | None = None,
    ) -> SeleniumAdapter:
        return SeleniumAdapter(
            self.connection,
            page_load_strategy=page_load_strategy,
            options=options,
            browser=browser,
            service=service,
            service_kwargs=service_kwargs,
            webdriver_kwargs=webdriver_kwargs,
            probe_timeout=self._resource.config.browser_probe_timeout,
        )

    def playwright(
        self,
        *,
        timeout: float | None = None,
        slow_mo: float | None = None,
        headers: Mapping[str, str] | None = None,
        is_local: bool | None = None,
        no_defaults: bool = True,
        artifacts_dir: str | None = None,
        connect_kwargs: Mapping[str, Any] | None = None,
    ) -> PlaywrightAdapter:
        return PlaywrightAdapter(
            self.connection,
            timeout=timeout,
            slow_mo=slow_mo,
            headers=headers,
            is_local=is_local,
            no_defaults=no_defaults,
            artifacts_dir=artifacts_dir,
            connect_kwargs=connect_kwargs,
        )

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        try:
            self.stop()
        except Exception:
            if exc is None:
                raise
        return False


class AsyncBrowserSession(AbstractAsyncContextManager["AsyncBrowserSession"]):
    """Async owner of one AdsPower browser process."""

    def __init__(
        self,
        *,
        profile_id: str | None,
        profile_no: str | None,
        connection: BrowserConnection,
        resource: "AsyncBrowsersResource",
    ) -> None:
        self.profile_id = profile_id
        self.profile_no = profile_no
        self.connection = connection
        self._resource = resource
        self._stopped = False

    async def __aenter__(self) -> "AsyncBrowserSession":
        return self

    async def stop(self) -> None:
        if not self._stopped:
            await self._resource.stop(self.profile_id, profile_no=self.profile_no)
            self._stopped = True

    def playwright(
        self,
        *,
        timeout: float | None = None,
        slow_mo: float | None = None,
        headers: Mapping[str, str] | None = None,
        is_local: bool | None = None,
        no_defaults: bool = True,
        artifacts_dir: str | None = None,
        connect_kwargs: Mapping[str, Any] | None = None,
    ) -> AsyncPlaywrightAdapter:
        return AsyncPlaywrightAdapter(
            self.connection,
            timeout=timeout,
            slow_mo=slow_mo,
            headers=headers,
            is_local=is_local,
            no_defaults=no_defaults,
            artifacts_dir=artifacts_dir,
            connect_kwargs=connect_kwargs,
        )

    async def __aexit__(self, exc_type: object, exc: BaseException | None, traceback: object) -> bool:
        try:
            await self.stop()
        except Exception:
            if exc is None:
                raise
        return False


def _running(value: object, config: AdsPowerConfig) -> tuple[RunningBrowser, ...]:
    if isinstance(value, list):
        raw = value
    else:
        data = require_object(value, field="opened browsers")
        raw = require_list(data.get("list", data.get("items")), field="opened browsers")
    result = []
    for item in raw:
        parsed = parse_running_browser(item)
        result.append(
            RunningBrowser(
                parsed.profile_id,
                resolve_browser_connection(parsed.connection, config),
                parsed.extra,
            )
        )
    return tuple(result)


def _cloud(value: object) -> tuple[CloudBrowserStatus, ...]:
    if isinstance(value, list):
        raw = value
    else:
        data = require_object(value, field="cloud status")
        raw = require_list(data.get("list", data.get("items")), field="cloud status")
    return tuple(parse_cloud_browser_status(item) for item in raw)


class BrowsersResource:
    """Synchronous browser process operations."""

    def __init__(self, transport: SyncTransportProtocol, config: AdsPowerConfig) -> None:
        self._transport = transport
        self.config = config

    def start(
        self,
        profile_id: str | None = None,
        *,
        profile_no: str | None = None,
        ip_tab: bool | None = None,
        launch_args: str | Sequence[str] | None = None,
        headless: bool | None = None,
        last_opened_tabs: bool | None = None,
        proxy_detection: bool | None = None,
        password_filling: bool | None = None,
        password_saving: bool | None = None,
        delete_cache: bool | None = None,
        cdp_mask: bool | None = None,
        device_scale: int | float | str | None = None,
        start_maximized: bool = False,
        timeout: float | None = None,
    ) -> BrowserSession:
        body = build_start_payload(
            profile_id,
            profile_no,
            ip_tab=ip_tab,
            launch_args=launch_args,
            headless=headless,
            last_opened_tabs=last_opened_tabs,
            proxy_detection=proxy_detection,
            password_filling=password_filling,
            password_saving=password_saving,
            delete_cache=delete_cache,
            cdp_mask=cdp_mask,
            device_scale=device_scale,
            start_maximized=start_maximized,
        )
        response = self._transport.request(
            c.PROFILE_START.method,
            c.PROFILE_START.path,
            json=body,
            timeout=timeout if timeout is not None else self.config.browser_start_timeout,
        )
        connection = resolve_browser_connection(
            parse_browser_connection(response_data(response, c.PROFILE_START)),
            self.config,
        )
        return BrowserSession(
            profile_id=profile_id,
            profile_no=profile_no,
            connection=connection,
            resource=self,
        )

    session = start

    def stop(self, profile_id: str | None = None, *, profile_no: str | None = None) -> None:
        response_data(
            self._transport.request(
                c.PROFILE_STOP.method,
                c.PROFILE_STOP.path,
                json=selector(profile_id, profile_no),
            ),
            c.PROFILE_STOP,
        )

    def stop_all(self) -> None:
        response_data(
            self._transport.request(c.PROFILE_STOP_ALL.method, c.PROFILE_STOP_ALL.path, json={}),
            c.PROFILE_STOP_ALL,
        )

    def status(self, profile_id: str | None = None, *, profile_no: str | None = None) -> BrowserStatus:
        payload = selector(profile_id, profile_no)
        params = {key: str(value) for key, value in payload.items()}
        data = response_data(
            self._transport.request(c.PROFILE_ACTIVE.method, c.PROFILE_ACTIVE.path, params=params),
            c.PROFILE_ACTIVE,
        )
        parsed = parse_browser_status(data)
        if parsed.connection is None:
            return parsed
        return BrowserStatus(
            parsed.status,
            resolve_browser_connection(parsed.connection, self.config),
            parsed.extra,
        )

    def list_opened(self) -> tuple[RunningBrowser, ...]:
        data = response_data(
            self._transport.request(c.PROFILE_LOCAL_ACTIVE.method, c.PROFILE_LOCAL_ACTIVE.path),
            c.PROFILE_LOCAL_ACTIVE,
        )
        return _running(data, self.config)

    def cloud_status(self, profile_ids: Sequence[str]) -> tuple[CloudBrowserStatus, ...]:
        ids = id_list(profile_ids, name="profile_ids", maximum=100)
        data = response_data(
            self._transport.request(
                c.PROFILE_CLOUD_ACTIVE.method,
                c.PROFILE_CLOUD_ACTIVE.path,
                json={"user_ids": ",".join(str(item) for item in ids)},
            ),
            c.PROFILE_CLOUD_ACTIVE,
        )
        return _cloud(data)


class AsyncBrowsersResource:
    """Asynchronous browser process operations."""

    def __init__(self, transport: AsyncTransportProtocol, config: AdsPowerConfig) -> None:
        self._transport = transport
        self.config = config

    async def start(
        self,
        profile_id: str | None = None,
        *,
        profile_no: str | None = None,
        ip_tab: bool | None = None,
        launch_args: str | Sequence[str] | None = None,
        headless: bool | None = None,
        last_opened_tabs: bool | None = None,
        proxy_detection: bool | None = None,
        password_filling: bool | None = None,
        password_saving: bool | None = None,
        delete_cache: bool | None = None,
        cdp_mask: bool | None = None,
        device_scale: int | float | str | None = None,
        start_maximized: bool = False,
        timeout: float | None = None,
    ) -> AsyncBrowserSession:
        body = build_start_payload(
            profile_id,
            profile_no,
            ip_tab=ip_tab,
            launch_args=launch_args,
            headless=headless,
            last_opened_tabs=last_opened_tabs,
            proxy_detection=proxy_detection,
            password_filling=password_filling,
            password_saving=password_saving,
            delete_cache=delete_cache,
            cdp_mask=cdp_mask,
            device_scale=device_scale,
            start_maximized=start_maximized,
        )
        response = await self._transport.request(
            c.PROFILE_START.method,
            c.PROFILE_START.path,
            json=body,
            timeout=timeout if timeout is not None else self.config.browser_start_timeout,
        )
        connection = resolve_browser_connection(
            parse_browser_connection(response_data(response, c.PROFILE_START)),
            self.config,
        )
        return AsyncBrowserSession(
            profile_id=profile_id,
            profile_no=profile_no,
            connection=connection,
            resource=self,
        )

    session = start

    async def stop(self, profile_id: str | None = None, *, profile_no: str | None = None) -> None:
        response_data(
            await self._transport.request(
                c.PROFILE_STOP.method,
                c.PROFILE_STOP.path,
                json=selector(profile_id, profile_no),
            ),
            c.PROFILE_STOP,
        )

    async def stop_all(self) -> None:
        response_data(
            await self._transport.request(c.PROFILE_STOP_ALL.method, c.PROFILE_STOP_ALL.path, json={}),
            c.PROFILE_STOP_ALL,
        )

    async def status(
        self,
        profile_id: str | None = None,
        *,
        profile_no: str | None = None,
    ) -> BrowserStatus:
        payload = selector(profile_id, profile_no)
        params = {key: str(value) for key, value in payload.items()}
        data = response_data(
            await self._transport.request(c.PROFILE_ACTIVE.method, c.PROFILE_ACTIVE.path, params=params),
            c.PROFILE_ACTIVE,
        )
        parsed = parse_browser_status(data)
        if parsed.connection is None:
            return parsed
        return BrowserStatus(
            parsed.status,
            resolve_browser_connection(parsed.connection, self.config),
            parsed.extra,
        )

    async def list_opened(self) -> tuple[RunningBrowser, ...]:
        data = response_data(
            await self._transport.request(c.PROFILE_LOCAL_ACTIVE.method, c.PROFILE_LOCAL_ACTIVE.path),
            c.PROFILE_LOCAL_ACTIVE,
        )
        return _running(data, self.config)

    async def cloud_status(self, profile_ids: Sequence[str]) -> tuple[CloudBrowserStatus, ...]:
        ids = id_list(profile_ids, name="profile_ids", maximum=100)
        data = response_data(
            await self._transport.request(
                c.PROFILE_CLOUD_ACTIVE.method,
                c.PROFILE_CLOUD_ACTIVE.path,
                json={"user_ids": ",".join(str(item) for item in ids)},
            ),
            c.PROFILE_CLOUD_ACTIVE,
        )
        return _cloud(data)

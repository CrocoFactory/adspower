from __future__ import annotations

import asyncio
import os
import threading
import uuid
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from adspower import AdsPowerClient, AdsPowerRatePolicy, AsyncAdsPowerClient, StoredProxyConfig

pytestmark = pytest.mark.integration


def _client() -> AdsPowerClient:
    return AdsPowerClient(rate_policy=AdsPowerRatePolicy.conservative())


def _async_client() -> AsyncAdsPowerClient:
    return AsyncAdsPowerClient(rate_policy=AdsPowerRatePolicy.conservative())


def _integration_enabled() -> None:
    if os.getenv("ADSPOWER_INTEGRATION") != "1":
        pytest.skip("Set ADSPOWER_INTEGRATION=1 to run real browser tests")


def _integration_profile_id() -> str:
    _integration_enabled()
    profile_id = os.getenv("ADSPOWER_TEST_PROFILE_ID")
    if not profile_id:
        pytest.skip("ADSPOWER_TEST_PROFILE_ID is required")
    return profile_id


def test_real_disposable_profile_crud_and_catalog_reads() -> None:
    _integration_enabled()
    profile_id: str | None = None
    profile_name = f"adspower-sdk-integration-{uuid.uuid4().hex}"
    with _client() as client:
        groups = client.groups.list(page_size=1)
        categories = client.categories.list(page_size=1)
        group_id = os.getenv("ADSPOWER_TEST_GROUP_ID") or (groups.items[0].group_id if groups.items else "0")
        try:
            created = client.profiles.create(name=profile_name, group_id=group_id)
            profile_id = created.profile_id
            assert client.profiles.get(profile_id).name == profile_name
            client.profiles.update(profile_id, name=f"{profile_name}-updated")
            assert client.profiles.get(profile_id).name == f"{profile_name}-updated"
            assert any(item.profile_id == profile_id for item in client.profiles.list(profile_id=profile_id).items)
            assert isinstance(client.profiles.cookies(profile_id=profile_id), tuple)
            client.profiles.delete_cache([profile_id], ["cookie"])
            assert hasattr(categories, "items")
        finally:
            if profile_id is not None:
                client.profiles.delete(profile_id)


def test_real_disposable_proxy_crud() -> None:
    _integration_enabled()
    host = os.getenv("ADSPOWER_TEST_PROXY_HOST")
    port = os.getenv("ADSPOWER_TEST_PROXY_PORT")
    if not host or not port:
        if os.getenv("ADSPOWER_REQUIRE_PROXY_INTEGRATION") == "1":
            pytest.fail("ADSPOWER_TEST_PROXY_HOST and ADSPOWER_TEST_PROXY_PORT are required by this integration gate")
        pytest.skip("ADSPOWER_TEST_PROXY_HOST and ADSPOWER_TEST_PROXY_PORT are required")

    proxy_id: str | None = None
    with _client() as client:
        try:
            ids = client.proxies.create(
                StoredProxyConfig(
                    proxy_type=os.getenv("ADSPOWER_TEST_PROXY_TYPE", "http"),  # type: ignore[arg-type]
                    host=host,
                    port=port,
                    user=os.getenv("ADSPOWER_TEST_PROXY_USER"),
                    password=os.getenv("ADSPOWER_TEST_PROXY_PASSWORD"),
                    remark="adspower-sdk-integration",
                )
            )
            proxy_id = ids[0]
            assert any(item.proxy_id == proxy_id for item in client.proxies.list(proxy_ids=[proxy_id]).items)
            client.proxies.update(
                proxy_id,
                port=int(port),
                remark="adspower-sdk-integration-updated",
            )
        finally:
            if proxy_id is not None:
                client.proxies.delete(proxy_id)


@pytest.fixture(scope="module")
def test_page_url() -> Iterator[str]:
    _integration_profile_id()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = b"<!doctype html><title>AdsPower SDK Test</title><p id='message'>hello</p>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/hello"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_real_selenium_attach(test_page_url: str) -> None:
    from selenium.webdriver.common.by import By

    with _client() as client:
        with client.browsers.session(_integration_profile_id(), headless=False) as session:
            with session.selenium() as driver:
                driver.get(test_page_url)
                assert driver.find_element(By.ID, "message").text == "hello"
                assert driver.execute_script("return document.title") == "AdsPower SDK Test"


def test_real_sync_playwright_attach(test_page_url: str) -> None:
    with _client() as client:
        with client.browsers.session(_integration_profile_id()) as session:
            with session.playwright() as browser:
                assert browser.is_connected()
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(test_page_url)
                assert page.locator("#message").inner_text() == "hello"


@pytest.mark.asyncio
async def test_real_async_playwright_attach(test_page_url: str) -> None:
    async with _async_client() as client:
        async with await client.browsers.session(_integration_profile_id()) as session:
            async with session.playwright() as browser:
                assert browser.is_connected()
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto(test_page_url)
                assert await page.locator("#message").inner_text() == "hello"


def _high_impact_enabled() -> None:
    _integration_enabled()
    if os.getenv("ADSPOWER_HIGH_IMPACT_INTEGRATION") != "1":
        if os.getenv("ADSPOWER_REQUIRE_HIGH_IMPACT") == "1":
            pytest.fail("ADSPOWER_HIGH_IMPACT_INTEGRATION=1 is required by this release gate")
        pytest.skip("Set ADSPOWER_HIGH_IMPACT_INTEGRATION=1 on a dedicated test installation")


@pytest.mark.asyncio
async def test_real_async_playwright_cancellation_cleanup(test_page_url: str) -> None:
    profile_id = _integration_profile_id()
    async with _async_client() as client:
        with pytest.raises(asyncio.CancelledError):
            async with await client.browsers.session(profile_id) as session:
                async with session.playwright() as browser:
                    context = browser.contexts[0]
                    page = context.pages[0] if context.pages else await context.new_page()
                    await page.goto(test_page_url)
                    asyncio.current_task().cancel()  # type: ignore[union-attr]
                    await asyncio.sleep(0)

        status = await client.browsers.status(profile_id)
        assert not status.active


def test_real_high_impact_profile_operations() -> None:
    _high_impact_enabled()
    profile_id = _integration_profile_id()
    receiver = os.getenv("ADSPOWER_TEST_SHARE_RECEIVER")
    if not receiver:
        pytest.fail("ADSPOWER_TEST_SHARE_RECEIVER is required for the high-impact release gate")

    with _client() as client:
        client.profiles.new_fingerprint(profile_ids=[profile_id])
        client.profiles.share([profile_id], receiver)
        client.browsers.stop_all()


def test_real_high_impact_kernel_download() -> None:
    _high_impact_enabled()
    kernel_type = os.getenv("ADSPOWER_TEST_KERNEL_TYPE", "Chrome")
    kernel_version = os.getenv("ADSPOWER_TEST_KERNEL_VERSION")
    if not kernel_version:
        pytest.fail("ADSPOWER_TEST_KERNEL_VERSION is required for the high-impact release gate")

    with _client() as client:
        client.kernels.download(kernel_type, kernel_version)  # type: ignore[arg-type]


def test_real_high_impact_patch_update() -> None:
    _high_impact_enabled()
    with _client() as client:
        client.app.update_patch(os.getenv("ADSPOWER_TEST_PATCH_CHANNEL", "stable"))  # type: ignore[arg-type]

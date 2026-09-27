from __future__ import annotations

import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Iterator

import pytest

from adspower import AdsPowerClient, AsyncAdsPowerClient

pytestmark = pytest.mark.integration


def _integration_profile_id() -> str:
    if os.getenv("ADSPOWER_INTEGRATION") != "1":
        pytest.skip("Set ADSPOWER_INTEGRATION=1 to run real browser tests")
    profile_id = os.getenv("ADSPOWER_TEST_PROFILE_ID")
    if not profile_id:
        pytest.skip("ADSPOWER_TEST_PROFILE_ID is required")
    return profile_id


@pytest.fixture(scope="module")
def test_page_url() -> Iterator[str]:
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

    with AdsPowerClient() as client:
        session = client.browsers.start(_integration_profile_id(), headless=False)
        with session.selenium() as driver:
            driver.get(test_page_url)
            assert driver.find_element(By.ID, "message").text == "hello"
            assert driver.execute_script("return document.title") == "AdsPower SDK Test"
            original = driver.current_window_handle
            driver.switch_to.new_window("tab")
            assert len(driver.window_handles) >= 2
            driver.close()
            driver.switch_to.window(original)
        session.stop()


def test_real_sync_playwright_attach(test_page_url: str) -> None:
    with AdsPowerClient() as client:
        session = client.browsers.start(_integration_profile_id())
        with session.playwright() as browser:
            assert browser.is_connected()
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(test_page_url)
            assert page.locator("#message").inner_text() == "hello"
            assert page.evaluate("document.title") == "AdsPower SDK Test"
            second = context.new_page()
            second.close()
        session.stop()


@pytest.mark.asyncio
async def test_real_async_playwright_attach(test_page_url: str) -> None:
    async with AsyncAdsPowerClient() as client:
        session = await client.browsers.start(_integration_profile_id())
        async with session.playwright() as browser:
            assert browser.is_connected()
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(test_page_url)
            assert await page.locator("#message").inner_text() == "hello"
            assert await page.evaluate("document.title") == "AdsPower SDK Test"
            second = await context.new_page()
            await second.close()
        await session.stop()

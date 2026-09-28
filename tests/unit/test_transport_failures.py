from __future__ import annotations

import httpx
import pytest

from adspower import (
    AdsPowerClient,
    AdsPowerConnectionError,
    AdsPowerTimeoutError,
    AsyncAdsPowerClient,
)


class RaisingTransport(httpx.BaseTransport):
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        raise self.exc


class AsyncRaisingTransport(httpx.AsyncBaseTransport):
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        raise self.exc


@pytest.mark.parametrize(
    ("exc", "error"),
    [
        (httpx.ConnectError("boom"), AdsPowerConnectionError),
        (httpx.ReadTimeout("boom"), AdsPowerTimeoutError),
    ],
)
def test_sync_transport_translates_network_failures(exc: Exception, error: type[Exception]) -> None:
    with AdsPowerClient(transport=RaisingTransport(exc)) as client:
        with pytest.raises(error):
            client.health.status()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exc", "error"),
    [
        (httpx.ConnectError("boom"), AdsPowerConnectionError),
        (httpx.ReadTimeout("boom"), AdsPowerTimeoutError),
    ],
)
async def test_async_transport_translates_network_failures(
    exc: Exception,
    error: type[Exception],
) -> None:
    async with AsyncAdsPowerClient(transport=AsyncRaisingTransport(exc)) as client:
        with pytest.raises(error):
            await client.health.status()

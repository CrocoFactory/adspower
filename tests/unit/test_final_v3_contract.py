from __future__ import annotations

import httpx
import pytest

from adspower import (
    AdsPowerClient,
    AdsPowerValidationError,
    AsyncAdsPowerClient,
    BrowserKernelConfig,
    FingerprintConfig,
    InlineProxyConfig,
    StoredProxyConfig,
)
from adspower.resources.profiles import _profile_fields, _profile_list_body


def ok(data: object = None) -> httpx.Response:
    return httpx.Response(200, json={"code": 0, "msg": "ok", "data": data})


def test_pinned_pagination_limits() -> None:
    with AdsPowerClient(transport=httpx.MockTransport(lambda request: ok({"list": []}))) as client:
        client.profiles.list(page_size=200)
        client.groups.list(page_size=100)
        client.categories.list(page_size=100)
        client.proxies.list(page_size=200)
        client.tags.list(page_size=200)

        with pytest.raises(AdsPowerValidationError):
            client.profiles.list(page_size=201)
        with pytest.raises(AdsPowerValidationError):
            client.groups.list(page_size=101)
        with pytest.raises(AdsPowerValidationError):
            client.categories.list(page_size=101)
        with pytest.raises(AdsPowerValidationError):
            client.proxies.list(page_size=201)
        with pytest.raises(AdsPowerValidationError):
            client.tags.list(page_size=201)


def test_profile_request_validation_matches_pinned_contract() -> None:
    assert _profile_fields({"profile_tag_ids": ["a"] * 30}, create=False)["profile_tag_ids"] == ["a"] * 30
    with pytest.raises(AdsPowerValidationError):
        _profile_fields({"profile_tag_ids": ["a"] * 31}, create=False)
    with pytest.raises(AdsPowerValidationError):
        _profile_fields({"tabs": [object()]}, create=False)
    with pytest.raises(AdsPowerValidationError):
        _profile_fields({"launch_args": ["--ok", object()]}, create=False)
    with pytest.raises(AdsPowerValidationError):
        _profile_fields({"country": "US"}, create=False)
    with pytest.raises(AdsPowerValidationError):
        _profile_list_body(
            group_id=None,
            profile_id=[1],  # type: ignore[list-item]
            profile_no=None,
            sort_type=None,
            sort_order=None,
            tag_ids=None,
            tags_filter=None,
            name=None,
            name_filter=None,
            page=1,
            page_size=200,
        )


@pytest.mark.asyncio
async def test_sync_async_profile_list_serialization_is_identical() -> None:
    sync_requests: list[bytes] = []
    async_requests: list[bytes] = []

    def sync_handler(request: httpx.Request) -> httpx.Response:
        sync_requests.append(request.content)
        return ok({"list": [], "page": 2, "page_size": 50})

    async def async_handler(request: httpx.Request) -> httpx.Response:
        async_requests.append(request.content)
        return ok({"list": [], "page": 2, "page_size": 50})

    kwargs = dict(
        group_id="0",
        profile_id=["p1"],
        sort_type="created_time",
        sort_order="desc",
        tag_ids=["t1"],
        tags_filter="include",
        name="shop",
        name_filter="include",
        page=2,
        page_size=50,
    )
    with AdsPowerClient(transport=httpx.MockTransport(sync_handler)) as client:
        client.profiles.list(**kwargs)  # type: ignore[arg-type]
    async with AsyncAdsPowerClient(transport=httpx.MockTransport(async_handler)) as client:
        await client.profiles.list(**kwargs)  # type: ignore[arg-type]

    assert sync_requests == async_requests


def test_verified_proxy_and_kernel_contracts() -> None:
    assert StoredProxyConfig("http", "host", 65536).to_api()["port"] == "65536"
    assert InlineProxyConfig("brightdata", port=65536).to_api()["proxy_port"] == "65536"
    with pytest.raises(AdsPowerValidationError):
        StoredProxyConfig("http", "host", 65537)
    with pytest.raises(AdsPowerValidationError):
        BrowserKernelConfig("firefox", "142")
    with pytest.raises(AdsPowerValidationError):
        FingerprintConfig(
            browser_kernel=BrowserKernelConfig("firefox", "141"),
            tls_enabled=True,
            tls="0xC02C",
        )


def test_paginated_iterators_exist_for_all_supported_resources() -> None:
    assert hasattr(AdsPowerClient, "__enter__")
    # The methods are intentionally part of the resource surface, not hidden helpers.
    with AdsPowerClient(transport=httpx.MockTransport(lambda request: ok({"list": []}))) as client:
        assert callable(client.groups.iter_all)
        assert callable(client.categories.iter_all)
        assert callable(client.proxies.iter_all)
        assert callable(client.tags.iter_all)

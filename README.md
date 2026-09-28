# AdsPower Python SDK

<p align="center">
  <a href="https://www.adspower.com">
    <img src="https://raw.githubusercontent.com/CrocoFactory/adspower/main/branding/adspower/banner.png" alt="AdsPower Python SDK" width="720">
  </a>
</p>

<p align="center">
  <a href="https://github.com/CrocoFactory/adspower/actions/workflows/ci.yml?query=branch%3Amain"><img src="https://github.com/CrocoFactory/adspower/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI status"></a>
  <a href="https://pypi.org/project/adspower/"><img src="https://img.shields.io/pypi/v/adspower?color=1d4dff" alt="PyPI version"></a>
  <a href="https://pypi.org/project/adspower/"><img src="https://img.shields.io/pypi/pyversions/adspower?color=1d4dff" alt="Python versions"></a>
  <a href="https://github.com/CrocoFactory/adspower/blob/main/LICENSE"><img src="https://img.shields.io/github/license/CrocoFactory/adspower" alt="License"></a>
</p>

Typed synchronous and asynchronous clients for AdsPower Local API. The SDK
covers profile, proxy and tag operations plus Selenium and Playwright browser
attachment. It preserves the server response envelope and does not forward an
AdsPower API key to CDP, WebDriver, or browser-version probes.

## What is verified

The current v3 implementation has deterministic contract tests and a live Local
API test pass. The live pass exercised temporary, automatically deleted profiles,
proxies and tags; it covered:

- sync and async profile CRUD, filtering, move, cookies, UA, fingerprint and cache operations;
- sync and async proxy and tag CRUD;
- health, groups, categories and kernel listing;
- browser start, status, opened-browser listing, cloud-status and stop;
- Selenium, sync Playwright, async Playwright, and async cancellation cleanup.

The checked non-integration suite has a 90% coverage gate. A real AdsPower
installation can still differ by app version, account permissions, installed
browser kernels, or network topology. Read the [Local API contract](docs/local-api-contract.md)
before treating an endpoint as version-independent.

Operations that affect an entire AdsPower installation or another account are
intentionally not part of the disposable live test: `stop_all`, profile sharing,
kernel download and app update. Run those only on a dedicated test installation.

## Requirements

- Python 3.10–3.15.
- AdsPower running with Local API enabled.
- An API key when the Local API installation requires one.
- Selenium and/or Playwright only for browser automation.

## Installation

```bash
pip install adspower
pip install 'adspower[selenium]'
pip install 'adspower[playwright]'
pip install 'adspower[all]'
```

## Quick start: Selenium

```python
from adspower import AdsPowerClient, AdsPowerRatePolicy

with AdsPowerClient(
    base_url="http://127.0.0.1:50325",
    api_key="your-api-key",
    rate_policy=AdsPowerRatePolicy.for_profile_count(200),
) as client:
    created = client.profiles.create(name="example")

    with client.browsers.session(created.profile_id, headless=True) as session:
        with session.selenium() as driver:
            driver.get("https://example.com")
            print(driver.title)

    client.profiles.delete(created.profile_id)
```

`BrowserSession` owns the AdsPower browser lifecycle. Exiting the session stops
the profile even if an attached driver raises an exception.

## Quick start: async Playwright

```python
import asyncio

from adspower import AdsPowerRatePolicy, AsyncAdsPowerClient


async def main() -> None:
    async with AsyncAdsPowerClient(
        api_key="your-api-key",
        rate_policy=AdsPowerRatePolicy.conservative(),
    ) as client:
        async with await client.browsers.session("profile-id", headless=True) as session:
            async with session.playwright() as browser:
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto("https://example.com")
                print(await page.title())


asyncio.run(main())
```

By default, browser endpoints are used exactly as AdsPower returns them. This
avoids CDP WebSocket host-header failures on Local API installations. For a
remote or Docker topology where AdsPower returns unreachable loopback endpoints,
opt into `browser_endpoint_policy="rewrite_loopback_to_api_host"`; see
[configuration](docs/configuration.md).

## Profiles, proxies, and pagination

```python
from adspower import StoredProxyConfig

page = client.profiles.list(
    name="shop",
    name_filter="include",
    tag_ids=["tag-id"],
    tags_filter="include",
    page_size=100,  # AdsPower V2 allows 1–100
)

proxy_ids = client.proxies.create_many(
    [StoredProxyConfig("http", "127.0.0.1", 8080, remark="example")]
)

for profile in client.profiles.iter_all(group_id="0"):
    print(profile.profile_id)
```

`groups.list()` accepts pages up to 2000; `proxies.create_many()` accepts up to
500 proxy definitions. `AdsPowerRatePolicy` applies the documented 1 req/s
limits to profile/group listings, cookies, and UA generation in addition to the
global rate limit.

## Raw API

```python
envelope = client.raw.request("POST", "/api/v2/future-endpoint", json={"x": 1})
```

Raw paths must be root-relative. Absolute URLs are rejected so the Local API
authorization header cannot be sent to another host.

## Documentation

- [Configuration and topology](docs/configuration.md)
- [Profiles and browser sessions](docs/profiles-and-sessions.md)
- [Automation adapters](docs/automation.md)
- [Local API contract and release gates](docs/local-api-contract.md)
- [API coverage](docs/api-coverage.md)
- [Errors](docs/errors.md)
- [Migration 2.x → 3.x](docs/migration-2-to-3.md)

## Development checks

```bash
poetry install --all-extras
poetry run pytest -m 'not integration' --cov=adspower --cov-fail-under=90
poetry run ruff check adspower tests
poetry run pyright adspower
poetry build
poetry run twine check dist/*
```

Live tests are opt-in and require a disposable AdsPower profile:

```bash
ADSPOWER_INTEGRATION=1 ADSPOWER_TEST_PROFILE_ID=profile-id poetry run pytest -m integration
```

See the [MIT License](LICENSE).

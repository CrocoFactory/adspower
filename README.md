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

Typed synchronous and asynchronous clients for the current AdsPower Local API
V2, with safe Selenium and Playwright attachment. The SDK supports local,
Docker and private remote AdsPower deployments.

> Version 3 is a breaking release. The old `adspower.sync_api` and
> `adspower.async_api` packages were removed; use the clients shown below.

## Features

- Sync and async profile CRUD through AdsPower API V2.
- Profile regrouping, cache deletion, cookie retrieval, sharing, and paginated name search.
- Proxy list and extension category resources with sync/async parity.
- Browser start/stop with Selenium, sync Playwright and async Playwright.
- API-key authentication, configurable endpoints and timeouts.
- Docker/remote CDP endpoint handling.
- Forward-compatible response models that preserve unknown fields.
- Optional, concurrency-safe rate limiting.
- Python 3.10–3.15 support.

## Requirements

- Python 3.10 or newer (through 3.15).
- AdsPower with Local API enabled and accessible to your account.
- Selenium and/or Playwright only when browser automation is needed.

AdsPower availability, permissions and rate limits depend on the installed
application version and account. See the [official Local API documentation](https://localapi-doc-en.adspower.com/).

## Installation

```bash
pip install adspower
pip install 'adspower[selenium]'
pip install 'adspower[playwright]'
pip install 'adspower[all]'
```

## Quick start: sync

```python
from adspower import AdsPowerClient, ScreenResolution

with AdsPowerClient(api_key="your-api-key") as client:
    profile = client.profiles.create(
        name="example",
        group_id="0",
        fingerprint_config={
            "screen_resolution": ScreenResolution.fixed(1920, 1080),
        },
    )

    session = client.browsers.start(profile.id)
    with session.selenium() as driver:
        driver.get("https://example.com")
```

`start_maximized` is opt-in. Headless mode belongs on the AdsPower start
request, not in Selenium options.

## Quick start: async Playwright

```python
import asyncio

from adspower import AsyncAdsPowerClient


async def main() -> None:
    async with AsyncAdsPowerClient(api_key="your-api-key") as client:
        profile = await client.profiles.get("profile-id")
        session = await client.browsers.start(profile.id)

        async with session.playwright() as browser:
            context = browser.contexts[0]
            page = context.pages[0]
            await page.goto("https://example.com")


asyncio.run(main())
```

The async client uses Playwright's exact CDP websocket returned by AdsPower and
disconnects before stopping the profile. Cleanup is idempotent.

## Profiles and groups

```python
profile = client.profiles.create(
    name="configured",
    group_id="0",
    user_proxy_config={
        "proxy_soft": "no_proxy",
    },
    fingerprint_config={
        "screen_resolution": "1366_768",
    },
)

profiles = client.profiles.list(group_id="0", page=1, page_size=100)
profile = client.profiles.get(profile.id)
profile = client.profiles.update(profile.id, name="renamed")
client.profiles.delete(profile.id)

group = client.groups.create("automation", remark="managed by SDK")
groups = client.groups.list(name=group.name)
```

`page_size` is translated to AdsPower V2's `limit` field. Profile IDs are
serialized in the shape expected by the current V2 API. When omitted, profile
creation receives a documented no-proxy configuration and a minimal valid
fingerprint configuration; explicit values always win.

`platform` is the account domain (for example `facebook.com`), not an operating
system. Browser-kernel selection belongs in `fingerprint_config`.

## Proxies, categories, and raw API

```python
proxy_ids = client.proxies.create(
    type="http", host="203.0.113.10", port="8000", remark="pool-a",
)
proxies = client.proxies.list(proxy_ids=proxy_ids)
categories = client.categories.list(page_size=100)

# Reach a new Local API endpoint before this SDK has a typed wrapper.
envelope = client.request(
    "POST", "/api/v2/future-endpoint", json={"future": "value"}, unwrap=False,
)
```

Raw requests accept only relative AdsPower paths, so the bearer token cannot be
sent accidentally to another host. Request errors include method/path context
but never include request payloads; model representations redact passwords,
cookies, API keys, 2FA secrets, and tokens.

## Configuration

The default endpoint is `http://127.0.0.1:50325`. Configure it directly or
through environment variables:

```bash
export ADSPOWER_BASE_URL=http://host.docker.internal:50325
export ADSPOWER_API_KEY=your-api-key
```

```python
from adspower import AdsPowerClient

client = AdsPowerClient(
    base_url="http://192.168.1.20:50325",
    api_key="your-api-key",
    timeout=60.0,
    browser_start_timeout=90.0,
)
```

API keys are sent as `Authorization: Bearer ...` and are redacted from client
representations. Keep a remote Local API port on a private network or VPN.

## Automation options

```python
session = client.browsers.start("profile-id", headless=True)

with session.selenium(
    start_maximized=True,
    page_load_strategy="eager",
) as driver:
    driver.get("https://example.com")
```

For sync Playwright:

```python
with client.browsers.start("profile-id").playwright() as browser:
    page = browser.contexts[0].pages[0]
    page.goto("https://example.com")
```

The SDK attaches to an existing AdsPower browser; it does not launch a bundled
Playwright Chromium. See [automation.md](docs/automation.md) for lifecycle and
manual cleanup options.

## Development

```bash
poetry install --all-extras
poetry run ruff check adspower tests
poetry run pytest -m "not integration" --cov --cov-fail-under=85
poetry build
```

Real Selenium/Playwright integration tests require an AdsPower installation and
a dedicated test profile. They are kept separate from deterministic mocked API
contract tests.

## Documentation

- [Documentation index](docs/INDEX.md)
- [Configuration and networking](docs/configuration.md)
- [Profiles and browser sessions](docs/profiles-and-sessions.md)
- [Automation adapters](docs/automation.md)
- [Migration from 2.x](docs/migration-2-to-3.md)
- [Development and release checks](docs/development.md)
- [Open issues](https://github.com/CrocoFactory/adspower/issues)

## License

MIT. See [LICENSE](LICENSE).

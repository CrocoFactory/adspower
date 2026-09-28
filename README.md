# AdsPower Python SDK v3

Typed synchronous and asynchronous clients for AdsPower Local API.

## Install

```bash
pip install adspower
pip install 'adspower[selenium]'
pip install 'adspower[playwright]'
```

## Sync

```python
from adspower import AdsPowerClient, FingerprintConfig, ScreenResolution

with AdsPowerClient(api_key="...") as client:
    created = client.profiles.create(
        name="example",
        fingerprint_config=FingerprintConfig(
            screen_resolution=ScreenResolution.fixed(1920, 1080)
        ),
    )
    profile = client.profiles.get(created.profile_id)

    with client.browsers.session(profile.profile_id) as session:
        with session.selenium() as driver:
            driver.get("https://example.com")
```

## Async Playwright

```python
import asyncio
from adspower import AsyncAdsPowerClient

async def main():
    async with AsyncAdsPowerClient(api_key="...") as client:
        async with await client.browsers.session("profile-id") as session:
            async with session.playwright() as browser:
                page = browser.contexts[0].pages[0]
                await page.goto("https://example.com")

asyncio.run(main())
```

## Profiles and pagination

```python
page = client.profiles.list(
    name="shop",
    name_filter="include",
    tag_ids=["tag-id"],
    tags_filter="include",
    page_size=200,
)
for profile in page.items:
    print(profile.profile_id)

for profile in client.profiles.iter_all(group_id="0"):
    ...
```

## Raw API

```python
envelope = client.raw.request("POST", "/api/v2/future-endpoint", json={"x": 1})
```

Raw paths must be root-relative, preventing credentials from being sent to a
different host.

## Docs

- [Architecture](docs/architecture.md)
- [Errors](docs/errors.md)
- [Local API contract](docs/local-api-contract.md)
- [API coverage](docs/api-coverage.md)
- [Automation](docs/automation.md)
- [Migration 2.x → 3.x](docs/migration-2-to-3.md)

The client-side rate limiter is a compliance guard, not an emulation of
AdsPower's undisclosed server algorithm. Live topology/automation claims are
release-gated; mocks are not treated as proof.

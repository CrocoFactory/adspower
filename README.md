# AdsPower Python SDK

Typed sync and async clients for the AdsPower Local API. Version 3 uses API V2
for browser profiles, keeps V1 behind an explicit compatibility namespace, and
supports local, Docker, and private remote deployments.

## Requirements

- Python 3.10–3.15
- AdsPower with Local API enabled for your account and installation
- Optional Selenium 4.x or Playwright 1.x for browser attachment

AdsPower API availability and rate limits can vary by endpoint, application
version, and account configuration. Check the official AdsPower documentation
for current service-side requirements.

## Installation

```bash
pip install adspower
pip install 'adspower[selenium]'
pip install 'adspower[playwright]'
pip install 'adspower[all]'
```

## Quick start

```python
from adspower import AdsPowerClient

with AdsPowerClient(api_key="secret") as client:
    profile = client.profiles.create(
        name="example",
        group_id="0",
        fingerprint_config={"screen_resolution": "1920_1080"},
    )
    session = client.browsers.start(profile.id, headless=False)

    with session.selenium() as driver:
        driver.get("https://example.com")
```

The default endpoint is `http://127.0.0.1:50325`. You can configure it directly
or with environment variables:

```bash
export ADSPOWER_BASE_URL=http://host.docker.internal:50325
export ADSPOWER_API_KEY=your-api-key
```

```python
from adspower import AdsPowerClient

client = AdsPowerClient(
    base_url="http://192.168.1.20:50325",
    api_key="secret",
    timeout=60.0,
)
```

API keys are sent as bearer tokens and are redacted from client representations.
Do not expose a remote Local API port directly to the public internet; use a
private network, VPN, and firewall controls.

## Async usage

```python
import asyncio

from adspower import AsyncAdsPowerClient


async def main() -> None:
    async with AsyncAdsPowerClient() as client:
        profile = await client.profiles.get("profile-id")
        session = await client.browsers.start(profile.id)

        async with session.playwright() as browser:
            context = browser.contexts[0]
            page = context.pages[0]
            await page.goto("https://example.com")


asyncio.run(main())
```

The browser adapter disconnects before stopping the AdsPower profile. Cleanup is
idempotent, and cleanup failures do not replace an exception raised by user code
inside a context manager.

## Profile operations

```python
profiles = client.profiles.list(group_id="0", page=1, page_size=100)
profile = client.profiles.get("profile-id")
updated = client.profiles.update(profile.id, name="new-name")
client.profiles.delete(profile.id)
```

Response parsing tolerates fields added by AdsPower. Known values are exposed as
typed attributes and unknown values remain available through `profile.extra`.
`user_proxy_config` is preserved on the profile model.

Proxy provider names accept strings so new AdsPower providers do not require an
SDK release. Known names are available through `ProxySoftware` for autocomplete.

```python
from adspower import ProxySoftware, ScreenResolution

profile = client.profiles.create(
    name="configured",
    group_id="0",
    user_proxy_config={
        "proxy_soft": ProxySoftware.OTHER.value,
        "proxy_type": "http",
        "proxy_host": "proxy.internal",
        "proxy_port": "8080",
    },
    fingerprint_config={
        "screen_resolution": ScreenResolution.fixed(1920, 1080),
    },
)
```

AdsPower also accepts special screen-resolution values such as `random` and
`none` where supported by its current API.

## Browser automation

`headless` is sent to AdsPower when starting a browser. It is not injected into
Selenium options after attachment. Window maximization is opt-in and Selenium's
default page-load strategy is preserved unless explicitly overridden.

```python
session = client.browsers.start("profile-id", headless=True)

with session.selenium(
    start_maximized=False,
    page_load_strategy="eager",
) as driver:
    ...
```

Playwright connects to the exact CDP websocket returned by AdsPower. Selenium
uses the returned debugger address and AdsPower-provided WebDriver path when
present. Attach-only Playwright usage does not launch a bundled browser.

## V1 compatibility

V2 is the default in 3.x. V1 profile endpoints remain explicit:

```python
legacy_profile = client.v1.profiles.create(group_id="0", name="legacy")
legacy_profiles = client.v1.profiles.list(group_id="0")
```

The original module-level 2.x API remains importable for one migration cycle but
is deprecated. New code should use `AdsPowerClient` or `AsyncAdsPowerClient`.

## Documentation

- [Documentation index](docs/INDEX.md)
- [Configuration and networking](docs/configuration.md)
- [Profiles and browser sessions](docs/profiles-and-sessions.md)
- [Automation adapters](docs/automation.md)
- [Migrating from 2.x](docs/migration-2-to-3.md)
- [Development and release checks](docs/development.md)

## License

MIT. See [LICENSE](LICENSE).

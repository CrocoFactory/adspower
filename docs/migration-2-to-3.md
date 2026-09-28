# Migrating from 2.x to 3.x

**Purpose**: Move class-level V1 code to configured V2 clients without hidden global state.

## Main changes

Version 3 makes these intentional breaking changes:

- API V2 is the default for browser profiles;
- the old `adspower.sync_api` and `adspower.async_api` packages are removed;
- configuration belongs to a client instance;
- profile data and running browser sessions are separate objects;
- automatic window maximization is disabled;
- Selenium page-load strategy is unchanged unless requested;
- browser headless mode is configured in the AdsPower start request;
- Selenium and Playwright are optional dependencies;
- Python 3.10 is the minimum supported version.

## Client configuration

Before:

```python
from adspower.sync_api import HTTPClient

HTTPClient.set_port(50325)
HTTPClient.set_timeout(30)
```

After:

```python
from adspower import AdsPowerClient

client = AdsPowerClient(
    base_url="http://127.0.0.1:50325",
    api_key="secret",
    timeout=30,
)
```

Environment variables are also supported. Configuration no longer leaks between
unrelated clients through class-level state.

## Profile CRUD

Before:

```python
profiles = Profile.query(name="example")
profile = Profile.create(group=group, name="example")
profile.update(name="renamed")
profile.delete()
```

After:

```python
profiles = client.profiles.list(name="example")
profile = client.profiles.create(group_id=group.id, name="example")
profile = client.profiles.update(profile.id, name="renamed")
client.profiles.delete(profile.id)
```

V2 create returns its response directly instead of performing an implicit query.
Unknown response fields are stored in `profile.extra`.

## Browser lifecycle

Before, a profile object also started, attached to, and stopped a browser. In 3.x:

```python
profile = client.profiles.get("profile-id")
session = client.browsers.start(profile.id, headless=False)

with session.selenium() as driver:
    ...
```

The context manager disconnects automation and stops the session. Use
`stop_on_exit=False` when you want to call `session.stop()` yourself.

## Selenium behavior

If you depended on automatic maximization or `page_load_strategy="none"`, request
those behaviors explicitly:

```python
with session.selenium(
    start_maximized=True,
    page_load_strategy="none",
) as driver:
    ...
```

Do not add a Selenium headless argument when attaching. Pass `headless=True` to
`client.browsers.start` instead.

## Playwright behavior

Playwright now uses AdsPower's returned CDP websocket verbatim. This fixes Docker
and remote-host attachment where rebuilding `http://localhost:<port>` was wrong.

Async cleanup disconnects automation before stopping the profile and Playwright
runtime. Calling cleanup twice is safe.

The old `adspower.sync_api`, `adspower.async_api`, and V1 profile bridge were
removed in 3.0. Migrate profile operations to `client.profiles` and browser
operations to `client.browsers`.

## Dependency changes

Install only what the application needs:

```bash
pip install adspower
pip install 'adspower[selenium]'
pip install 'adspower[playwright]'
```

Supported ranges are HTTPX 0.27.2–0.x, Selenium 4.20–4.x, and Playwright
1.61–1.x. CI checks minimum and latest compatible dependency sets.

## References

- `README.md`
- `adspower/client.py`
- `pyproject.toml`

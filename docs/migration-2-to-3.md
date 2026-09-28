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
profiles = client.profiles.find_all_by_name("example")
profile = client.profiles.create(group_id=group.id, name="example")
client.profiles.update(profile.id, name="renamed")
profile = client.profiles.update(profile.id, name="renamed-again", refresh=True)
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
session = client.browsers.start("profile-id", start_maximized=True)

with session.selenium(
    page_load_strategy="none",
) as driver:
    ...
```

Do not add a Selenium headless argument when attaching. Pass `headless=True` to
`client.browsers.start` instead.

Legacy `user_proxy_config` aliases such as `host`, `port`, and `password` were
removed. Use the Local API V2 names (`proxy_host`, `proxy_port`, and
`proxy_password`); v3 rejects the old keys before sending a request.

## Playwright behavior

Playwright preserves AdsPower's returned CDP path/browser identifier. For remote
Local API deployments the default endpoint policy rewrites loopback hosts to the
configured API host; use `browser_host=` when browser debug ports live on a
different host, or `browser_endpoint_policy="exact"` to disable rewriting.
It also defaults to `no_defaults=True` to preserve the existing profile-managed
browser context.

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

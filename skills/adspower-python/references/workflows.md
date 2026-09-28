# AdsPower v3 workflow patterns

Load this reference when an implementation spans multiple SDK resources, launches a browser, handles a fleet, or needs a complete sync/async pattern.

## 1. Reuse an existing persistent profile with Playwright

Use this when the desired cookies/login/storage already belong to an AdsPower profile. Do not create a replacement profile just to automate it.

```python
from adspower import AdsPowerClient, AdsPowerRatePolicy


def run(profile_id: str) -> str:
    with AdsPowerClient(rate_policy=AdsPowerRatePolicy.conservative()) as client:
        with client.browsers.start(profile_id, headless=True) as session:
            with session.playwright() as browser:
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else context.new_page()
                page.goto("https://example.com")
                return page.title()
```

Why this shape matters:

- `start()` owns the AdsPower browser process and returns `BrowserSession`.
- `session.playwright()` owns only Playwright attachment/runtime cleanup.
- Exiting the inner context disconnects/cleans automation before the outer context asks AdsPower to stop the profile.

## 2. Reuse a profile with Selenium

```python
from adspower import AdsPowerClient

with AdsPowerClient() as client:
    with client.browsers.start("profile-id") as session:
        with session.selenium(page_load_strategy="eager") as driver:
            driver.get("https://example.com")
            print(driver.title)
```

Install the optional extra with `pip install 'adspower[selenium]'`. The async client does not expose an async Selenium adapter; use async Playwright for a fully async browser workflow.

## 3. Async persistent-profile workflow

```python
from adspower import AdsPowerRatePolicy, AsyncAdsPowerClient


async def run(profile_id: str) -> str:
    async with AsyncAdsPowerClient(
        rate_policy=AdsPowerRatePolicy.conservative(),
    ) as client:
        async with await client.browsers.start(profile_id, headless=True) as session:
            async with session.playwright() as browser:
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto("https://example.com")
                return await page.title()
```

Do not open one client per coroutine unless independent rate budgets are truly intended. Share the client within a worker and constrain concurrency around the business workflow as needed.

## 4. Create an ephemeral profile and always remove it

Creation returns only `CreatedProfile`. Keep profile deletion outside the browser-session context so the process is stopped before the profile is removed.

```python
from adspower import AdsPowerClient

with AdsPowerClient() as client:
    created = client.profiles.create(name="temporary-job")
    try:
        with client.browsers.start(created.profile_id, headless=True) as session:
            with session.playwright() as browser:
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else context.new_page()
                page.goto("https://example.com")
    finally:
        client.profiles.delete(created.profile_id)
```

If failure semantics make it unclear whether the profile was created, reconcile with `get`/`list` rather than blindly issuing another create.

## 5. Create a profile with a stored proxy

Create the proxy first, then use the returned proxy id in the profile. Do not assume `proxies.create()` returns a single string; the API returns a tuple of created IDs.

```python
from adspower import AdsPowerClient, StoredProxyConfig

with AdsPowerClient() as client:
    proxy_ids = client.proxies.create(
        StoredProxyConfig(
            proxy_type="http",
            host="127.0.0.1",
            port=8080,
            remark="job-proxy",
        )
    )
    proxy_id = proxy_ids[0]
    created = client.profiles.create(name="job", proxyid=proxy_id)
```

For a proxy only needed by one profile, consider `InlineProxyConfig` instead of polluting the reusable proxy store. When no proxy is requested, omit both fields; v3 supplies the first-party no-proxy value.

## 6. Set only the fingerprint fields the task requires

```python
from adspower import FingerprintConfig

fingerprint = FingerprintConfig(
    automatic_timezone=True,
    language_by_ip=True,
    canvas_noise=True,
)

created = client.profiles.create(
    name="example",
    fingerprint_config=fingerprint,
)
```

Do not generate a giant "realistic" fingerprint by guessing values. Fingerprint consistency is a domain concern; the SDK model exists to validate and translate supported fields.

## 7. Operate on a whole fleet without dropping pages

```python
for profile in client.profiles.iter_all(group_id="12"):
    print(profile.profile_id, profile.name)
```

Async:

```python
async for profile in client.profiles.iter_all(group_id="12"):
    print(profile.profile_id)
```

If the next step is destructive, materialize and inspect the target IDs/count before mutation rather than mutating inline while discovering pages.

## 8. Find an exact named profile

`find_by_name()` requests an include filter and then checks equality in the returned page. It is convenient for a known exact name, but names are not a universal identity. Prefer persisted `profile_id` for durable automation.

```python
profile = client.profiles.find_by_name("shop-eu")
if profile is None:
    ...
```

Do not treat the first substring match from `profiles.list(name=..., name_filter="include")` as an exact selection.

## 9. Docker/remote topology

Start with default exact endpoint behavior:

```python
client = AdsPowerClient(base_url="http://host.docker.internal:50325")
```

Only if AdsPower returns a loopback debugger/CDP host that is unreachable from the automation process:

```python
client = AdsPowerClient(
    base_url="http://host.docker.internal:50325",
    browser_endpoint_policy="rewrite_loopback_to_api_host",
)
```

If the API endpoint and browser endpoint need different reachable hosts, set `browser_host` to the browser host. Do not put a scheme or port in `browser_host`.

## 10. Use raw access for a real typed-surface gap

```python
result = client.raw.request(
    "GET",
    "/api/v2/new-endpoint",
    params={"profile_id": "..."},
)
```

Confirm the method/path and payload from current first-party AdsPower evidence. Keep the path root-relative. If this becomes common/stable behavior in the library, add a typed resource/model and contract tests.

## 11. Safe rate-limit recovery for reads

```python
import time

from adspower import AdsPowerRateLimitError

try:
    page = client.profiles.list(page_size=100)
except AdsPowerRateLimitError as exc:
    if exc.retry_after is None:
        raise
    time.sleep(exc.retry_after)
    page = client.profiles.list(page_size=100)
```

This pattern is appropriate only when the repeated operation is safe. Do not apply generic retry decorators to create/update/delete/share/start/stop calls without a reconciliation strategy.

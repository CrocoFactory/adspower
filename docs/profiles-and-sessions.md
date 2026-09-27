# Profiles and browser sessions

**Purpose**: Explain V2 profile operations and the separation between persistent profiles and running browsers.

## Profiles

`client.profiles` uses AdsPower API V2. A profile is persistent data; it does not
own a global client or an automation runtime.

```python
profile = client.profiles.create(name="example", group_id="0")
profile = client.profiles.get(profile.id)
profiles = client.profiles.list(group_id="0")
profile = client.profiles.update(profile.id, name="renamed")
client.profiles.delete(profile.id)
```

The SDK translates `page_size` to AdsPower V2's `limit` field and sends profile
IDs as arrays for V2 list and delete calls, as required by the current API.

Create returns the profile directly from the server response. It does not issue a
second list request just to recover an identifier.

Known response fields are normalized:

- `profile_id`, `user_id`, or `id` becomes `Profile.id`;
- `profile_no` or `serial_number` becomes `Profile.number`;
- `group_id` is represented as a string;
- `user_proxy_config` remains available as a dictionary;
- unrecognized fields are stored in `Profile.extra`.

This tolerant model prevents newly added AdsPower fields from breaking the SDK.

## Request schemas

Additional keyword arguments are passed through to the V2 request. `None` values
are omitted while false values, empty lists, and zero values are retained.
When omitted during creation, the SDK supplies AdsPower's documented no-proxy
configuration and a minimal valid fingerprint configuration. Explicit values
always take precedence.

```python
profile = client.profiles.create(
    name="example",
    group_id="0",
    platform="windows",
    tabs=["https://example.com"],
    user_proxy_config={"proxy_soft": "other"},
    fingerprint_config={"screen_resolution": "1366_768"},
)
```

Proxy-provider fields accept strings. This keeps the runtime forward-compatible
when AdsPower introduces a provider that the SDK does not know yet.

## Groups

AdsPower group operations remain on their established V1 endpoints because the
profile V2 contract does not provide equivalent group endpoints.

```python
group = client.groups.create("automation", remark="managed by SDK")
groups = client.groups.list(name="automation")
```

This is intentionally separate from `client.v1`, which represents the legacy
profile contract.

## Browser sessions

A browser session exists only after a profile is started:

```python
session = client.browsers.start(profile.id, headless=False)
print(session.connection.selenium)
print(session.connection.playwright_cdp)
session.stop()
```

`BrowserConnection` parses:

- Selenium debugger address;
- exact Playwright/Puppeteer CDP websocket;
- debug port;
- AdsPower-provided WebDriver path;
- future fields in `extra`.

Calling `stop()` more than once on the same session is safe and sends one stop
request. Automation context managers can stop automatically on exit.

## Async parity

The async API has the same service layout and shared parsers:

```python
profile = await client.profiles.create(name="example", group_id="0")
profiles = await client.profiles.list(group_id="0")
session = await client.browsers.start(profile.id)
await session.stop()
```

Only I/O orchestration differs. Request paths, serializers, models, response
handling, and exception mapping are shared with the sync API.

## V1 profile compatibility

Use the explicit namespace for old profile endpoints:

```python
profile = client.v1.profiles.create(group_id="0", name="legacy")
profiles = client.v1.profiles.list(group_id="0", page=1, page_size=100)
client.v1.profiles.delete(profile.id)
```

The V1 namespace is a migration bridge. Prefer V2 for new applications.

## References

- `adspower/models.py`
- `adspower/api.py`
- `adspower/client.py`
- `adspower/async_client.py`
- `adspower/legacy.py`

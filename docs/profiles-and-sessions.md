# Profiles and browser sessions

## Profiles

Creation returns identifiers, not a synthetic full snapshot:

```python
created = client.profiles.create(name="example", group_id="0")
profile = client.profiles.get(created.profile_id)
client.profiles.update(profile.profile_id, name="renamed")
client.profiles.delete(profile.profile_id)
```

`update()` returns `None`. Fetch explicitly with `get()` when a fresh
snapshot is required; mutations do not hide follow-up network calls.

Profile listing uses server-side name/tag filters and preserves pagination:

```python
page = client.profiles.list(
    name="shop",
    name_filter="include",
    tag_ids=["tag-id"],
    tags_filter="include",
    page_size=100,
)
for profile in client.profiles.iter_all(group_id="0"):
    print(profile.profile_id, profile.profile_no)
```

Known response fields are parsed strictly. Unknown fields remain available via
typed `extra` metadata. Canonical names are `profile_id` and `profile_no`;
there is no `id`, `number`, or intermediate-v3 compatibility property.

Creation injects only the first-party no-proxy value when neither `proxyid`
nor `user_proxy_config` is supplied. Fingerprint configuration is omitted
unless the caller supplies it.

## Groups, categories, proxies and tags

Paginated resources return `Page[T]` and provide `iter_all()` where the
underlying endpoint is paginated. Current first-party limits are enforced:
profiles 200/page, groups 100/page, categories 100/page, proxies 200/page and
tags 200/page.

## Browser sessions

```python
with client.browsers.session(profile_id=profile.profile_id) as session:
    print(session.connection.selenium_debugger_address)
    print(session.connection.playwright_cdp_url)
    with session.selenium() as driver:
        driver.get("https://example.com")
```

The outer `BrowserSession` owns AdsPower start/stop. Selenium and Playwright
adapters own only attachment and their own runtime cleanup. Adapter cleanup
happens before Local API stop, cleanup errors do not mask an existing user or
control-flow exception, and native automation runtime exceptions remain native.

Async exposes the same resource names and request semantics:

```python
page = await client.profiles.list(name="shop")
async for profile in client.profiles.iter_all(group_id="0"):
    ...
```

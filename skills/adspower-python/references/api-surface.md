# v3 typed API surface and limits

Load this reference when exact method names, return shapes, page/batch limits, or branch-specific API discrepancies matter. It was authored against `codex/v3-modernization@d19ff16c5e9a518b42eb0e13ceba75386e08832d`; prefer the current checkout if it has moved.

## Resource namespaces

Both `AdsPowerClient` and `AsyncAdsPowerClient` expose the same resource namespaces:

- `profiles`
- `browsers`
- `groups`
- `proxies`
- `categories`
- `tags`
- `kernels`
- `app`
- `health`
- `raw`

Async methods mirror sync request semantics; use `await` / async iteration where appropriate.

## Profiles

Core sync methods:

```text
profiles.create(*, group_id="0", name=None, **options) -> CreatedProfile
profiles.update(profile_id, **options) -> None
profiles.list(..., page=1, page_size=100) -> Page[Profile]
profiles.iter_all(...) -> Iterator[Profile]
profiles.get(profile_id) -> Profile
profiles.find_by_name(name, *, group_id=None) -> Profile | None
profiles.delete(profile_id) -> None
profiles.delete_many(profile_ids) -> None
profiles.move(profile_ids, group_id) -> None
profiles.cookies(*, profile_id=None, profile_no=None) -> tuple[JsonObject, ...]
profiles.user_agents(*, profile_ids=None, profile_nos=None) -> JsonValue
profiles.new_fingerprint(*, profile_ids=None, profile_nos=None) -> JsonValue | None
profiles.delete_cache(profile_ids, cache_types) -> None
profiles.share(profile_ids, receiver, *, share_type="email", content=None) -> JsonValue | None
```

Important constraints from the current source/contract:

- Profile list `page_size`: 1-100.
- `profile_tag_ids` on create/update: max 30.
- User-agent generation: exactly one of profile IDs/profile numbers; first-party contract max 10.
- New fingerprint: exactly one selector family; treat as high-impact.
- Share: first-party contract max 200 profiles; high-impact.
- `group_id` is represented as a numeric string.
- Country, when supplied, is a lowercase two-letter code.
- Create injects no-proxy configuration when no proxy field is supplied.

Known documentation drift: an older `docs/profiles-and-sessions.md` sentence may say profiles allow 200/page, but current `ProfilesResource.list` validates a maximum of 100 and `docs/local-api-contract.md` also records 1-100. Follow current source/contract.

## Browsers

Current sync source:

```text
browsers.start(profile_id=None, *, profile_no=None, ip_tab=None,
               launch_args=None, headless=None, last_opened_tabs=None,
               proxy_detection=None, password_filling=None,
               password_saving=None, delete_cache=None, cdp_mask=None,
               device_scale=None, start_maximized=False, timeout=None)
    -> BrowserSession
browsers.stop(profile_id=None, *, profile_no=None) -> None
browsers.stop_all() -> None
browsers.status(profile_id=None, *, profile_no=None) -> BrowserStatus
browsers.list_opened() -> tuple[RunningBrowser, ...]
browsers.cloud_status(profile_ids) -> tuple[CloudBrowserStatus, ...]
```

`cloud_status` accepts at most 100 IDs.

`BrowserSession`:

```text
session.stop() -> None
session.selenium(..., browser="chromium", ...) -> SeleniumAdapter
session.playwright(..., no_defaults=True, ...) -> PlaywrightAdapter
```

`AsyncBrowserSession` exposes async `stop()` and async Playwright attachment. It does not expose an async Selenium adapter.

### Browser method alias

`browsers.session` is a public alias of `browsers.start` in the current sync and async resources. Both return their respective browser-session context manager; for async, await the call before entering the session. The README's `.session(...)` examples are valid.

Do not decide that the alias is absent just because `browsers.py` has no separate `def session`. Verify the importable surface and alias relationship with `scripts/inspect_surface.py` when the installed package and checkout may differ.

## Groups

```text
groups.create(name, *, remark=None) -> Group
groups.update(group_id, *, name, remark=None) -> None
groups.list(*, name=None, page=1, page_size=10) -> Page[Group]
groups.iter_all(...) -> Iterator[Group]
```

Maximum group page size: 2000.

## Categories

```text
categories.list(*, category_id=None, page=1, page_size=100) -> Page[Category]
categories.iter_all(...) -> Iterator[Category]
```

Maximum category page size: 100.

## Proxies

```text
proxies.create(config: StoredProxyConfig) -> tuple[str, ...]
proxies.create_many(configs) -> tuple[str, ...]
proxies.update(proxy_id, **options) -> None
proxies.list(*, proxy_ids=None, page=1, page_size=50) -> Page[Proxy]
proxies.iter_all(...) -> Iterator[Proxy]
proxies.delete(proxy_id) -> None
proxies.delete_many(proxy_ids) -> None
```

Limits:

- Create batch: max 500.
- List page: max 200.
- Delete batch: max 100.

`StoredProxyConfig.proxy_type`: `http`, `https`, `ssh`, or `socks5` in current source.

## Tags

```text
tags.list(*, ids=None, page=1, page_size=50) -> Page[BrowserTag]
tags.iter_all(...) -> Iterator[BrowserTag]
tags.create(tags: Sequence[TagCreate]) -> JsonValue | None
tags.update(tags: Sequence[TagUpdate]) -> None
tags.delete(ids) -> None
```

Limits:

- List page: max 200.
- ID filter: max 100 IDs.
- Tag names: 1-50 characters.

## Kernels and application

```text
kernels.list(*, kernel_type="Chrome" | "Firefox" | None) -> tuple[KernelInfo, ...]
kernels.download(kernel_type, kernel_version) -> JsonValue | None
app.update_patch(version_type="stable" | "beta") -> JsonValue | None
```

Kernel download and application patch update are high-impact operations; do not use them as incidental setup.

## Raw

```text
raw.request(method, path, *, params=None, json=None, timeout=None, ...) -> envelope/data
```

The path must start with one `/`, be root-relative, and contain no scheme/netloc. This is a security boundary, not cosmetic validation.

## Return-type rules worth remembering

- `CreatedProfile` is only the creation result; fetch with `profiles.get()` for a current full `Profile`.
- Mutation methods generally return `None` unless the underlying endpoint has a meaningful creation/result payload.
- Paginated endpoints return `Page[T]`, preserving pagination metadata.
- Known response fields are typed; models may retain unknown server fields in `extra` rather than discarding them.

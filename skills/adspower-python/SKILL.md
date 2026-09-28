---
name: adspower-python
description: Use this skill when writing, reviewing, debugging, or migrating Python code that uses the CrocoFactory/adspower v3 SDK or accesses AdsPower Local API through this Python library. Trigger for AdsPower profile fleets, persistent browser sessions, proxies, groups/tags, Playwright or Selenium attachment, sync/async clients, rate limits, Docker/remote endpoint topology, raw forward-compatible calls, or v2-to-v3 migration. Do not use it for the separate AdsPower CLI/MCP package unless the task also uses this Python SDK.
license: MIT
compatibility: CrocoFactory/adspower v3; Python 3.10-3.15. Live operations require a reachable AdsPower Local API and any required API key. Playwright and Selenium are optional extras.
metadata:
  target-repository: CrocoFactory/adspower
  target-major-version: "3"
  authored-against-ref: "codex/v3-modernization@a219cb22831fe88f39b40de3e739982e7d04029c"
  skill-version: "0.1.0"
---

# AdsPower Python SDK v3

Use this skill to turn an AdsPower automation intent into code that follows this SDK's actual v3 contracts and lifecycle. It is deliberately not an API-documentation dump. Its highest-value job is to prevent plausible-but-wrong code around browser ownership, v2/v3 drift, pagination, topology, rate limits, and mutation semantics.

## Establish the source of truth

When working inside a checkout of this repository, resolve uncertainty in this order:

1. Current importable public surface and type signatures, including declared aliases.
2. Contract tests and `docs/local-api-contract.md` for wire behavior.
3. Other repository docs.
4. Current official AdsPower Local API documentation.
5. Historical v2 behavior only when explicitly migrating it.

If this skill disagrees with the current checkout, follow the checkout and update the skill. Never preserve an older API merely because an example online still uses it.

When the installed package may differ from the checkout, run:

```bash
python skills/adspower-python/scripts/inspect_surface.py
```

Use the report to confirm version, resource namespaces, and browser methods before emitting code that depends on a disputed surface.

## Route the task before coding

Choose the narrowest typed resource that owns the operation:

- Profile identity, cookies, fingerprint, grouping or profile metadata -> `client.profiles`.
- Browser process start/stop/status and automation attachment -> `client.browsers`.
- Reusable stored proxies -> `client.proxies`; per-profile inline proxy settings -> `InlineProxyConfig` during profile create/update.
- Fleet organization -> `client.groups`, `client.tags`, and `client.categories`.
- Browser kernels or AdsPower patch update -> `client.kernels` / `client.app`; treat these as high-impact operations.
- Unsupported/new Local API endpoint -> `client.raw.request(...)`, but only after confirming there is no typed wrapper.

Use one long-lived client per logical worker/process when practical. This preserves connection pooling and makes client-side rate limiting meaningful.

## Pick sync or async from the host application

Use `AdsPowerClient` in synchronous programs and `AsyncAdsPowerClient` in an existing async application. Their resource namespaces intentionally mirror each other.

Do not wrap the sync SDK in `asyncio.to_thread()` merely to imitate async. Use the async client instead.

For browser automation:

- Sync client: Playwright or Selenium are available through the returned `BrowserSession`.
- Async client: use async Playwright. Do not invent an async Selenium adapter.

Read `references/workflows.md` when the task spans multiple resources or needs a complete automation pattern.

## Browser lifecycle: start owns the process

`client.browsers.start(...)` returns the browser-session context manager. In the current v3 source, `client.browsers.session(...)` is a supported public alias of `start(...)` for both sync and async clients. The README's use of `.session(...)` is therefore valid.

Do not infer a missing public method from the absence of a matching `def`: Python aliases such as `session = start` are part of the surface. When this distinction matters, inspect the importable resource (or run `scripts/inspect_surface.py`) rather than grepping only for function definitions. Use either spelling consistently with the surrounding code.

Use nested ownership so the automation adapter closes before AdsPower stops the profile:

```python
from adspower import AdsPowerClient

with AdsPowerClient() as client:
    with client.browsers.start("profile-id", headless=True) as session:
        with session.playwright() as browser:
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://example.com")
```

Async equivalent:

```python
from adspower import AsyncAdsPowerClient

async with AsyncAdsPowerClient() as client:
    async with await client.browsers.start("profile-id", headless=True) as session:
        async with session.playwright() as browser:
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto("https://example.com")
```

Do not call `stop()` in a second cleanup path when the outer session context already owns it. If the user's code needs to keep a browser running after a function returns, make that lifecycle choice explicit rather than defeating the context manager accidentally.

## Preserve AdsPower's persistence model

AdsPower is commonly used because a profile carries long-lived browser state and identity. When the goal is to resume an authenticated or stable environment, reuse the requested profile rather than creating a fresh profile on every run.

Create a disposable profile only when the workflow actually calls for an ephemeral environment. For disposable workflows, delete the profile in an outer `finally` after its browser session is closed.

Never select an arbitrary first profile after a fuzzy search for a destructive operation. Resolve the intended `profile_id` explicitly, especially in fleet/batch tasks.

## Use v3 mutation and pagination semantics

Remember these non-obvious v3 contracts:

- `profiles.create(...)` returns `CreatedProfile`, not a full `Profile` snapshot.
- `profiles.update(...)` returns `None`; call `profiles.get(profile_id)` explicitly if the caller needs fresh state.
- List operations return `Page[T]` rather than a plain list.
- Use `iter_all()` / async iteration when the intent is "all profiles/proxies/tags/groups/categories"; do not silently operate on only page 1.
- Use canonical names such as `profile_id`, `profile_no`, and `proxy_type`; do not reintroduce v2 compatibility aliases.
- Supply Python booleans and SDK config objects. Do not hand-encode AdsPower's wire-level `"0"`/`"1"` values.

Read `references/api-surface.md` when exact method names, return types, current page/batch limits, or branch-specific discrepancies matter.

## Prefer typed models; do not fabricate fingerprint fields

Use `StoredProxyConfig`, `InlineProxyConfig`, `FingerprintConfig`, `PlatformAccount`, and other public models rather than hand-built JSON for typed endpoints.

Profile creation intentionally injects AdsPower's no-proxy representation when neither `proxyid` nor `user_proxy_config` is provided. Do not add a proxy merely because AdsPower profiles often use one.

Fingerprint configuration is broad and version-sensitive. Set only fields the task actually requires. For uncommon fingerprint fields, inspect `adspower/models/fingerprint.py` in the current checkout instead of guessing a field name from AdsPower's wire docs.

Read `references/config-models.md` when the task involves proxy models, fingerprint settings, environment variables, timeouts, or Docker/remote topology.

## Respect topology instead of rewriting endpoints by default

Keep `browser_endpoint_policy="exact"` unless the environment proves AdsPower's returned loopback debugger/CDP endpoint is unreachable from the automation process. Exact mode avoids breaking Local API setups that expect the returned host verbatim.

For Docker/remote deployments where AdsPower returns loopback endpoints that point to the wrong network namespace, opt into `"rewrite_loopback_to_api_host"` and set `browser_host` only when the API host is not the correct reachable browser host.

Never pass the AdsPower Local API `Authorization` header to CDP, WebDriver, or browser version probes. The SDK is designed to keep those trust boundaries separate; do not bypass that protection in helper code.

## Rate-limit deliberately

Prefer:

```python
from adspower import AdsPowerClient, AdsPowerRatePolicy

client = AdsPowerClient(
    rate_policy=AdsPowerRatePolicy.for_profile_count(200),
)
```

When profile count is unknown and correctness matters more than maximum throughput, use `AdsPowerRatePolicy.conservative()`.

The policy is client-side compliance logic, not a model of AdsPower's undisclosed server limiter. Separate clients/processes do not automatically share one budget. Do not solve a 429 by spawning more clients.

Do not automatically retry mutations. For a safe read that hits `AdsPowerRateLimitError`, honor `retry_after` when present and keep retries bounded. Treat ambiguous mutation failures as reconciliation problems: inspect server state before deciding whether to repeat the request.

## Use raw access only as a forward-compatibility escape hatch

If the endpoint has a typed wrapper, use it. For a genuinely newer/unwrapped Local API operation:

```python
envelope = client.raw.request(
    "POST",
    "/api/v2/future-endpoint",
    json={"x": 1},
)
```

Raw paths must be root-relative. Never construct an absolute URL or `//host/...`; the SDK rejects these so credentials cannot be redirected to another host.

When adding stable support to the library itself, promote a proven raw workflow into a typed model/resource rather than normalizing raw calls throughout the codebase.

## Handle errors by layer

Catch the narrowest SDK exception that the caller can actually recover from:

- configuration/input -> `AdsPowerConfigurationError` / `AdsPowerValidationError`;
- transport/DNS/socket -> `AdsPowerConnectionError`;
- timeout -> `AdsPowerTimeoutError`;
- server rejection -> `AdsPowerAPIError` and its auth/rate-limit subclasses;
- malformed/unexpected Local API response -> `AdsPowerProtocolError`;
- SDK convenience lookup miss -> `AdsPowerNotFoundError`.

Do not classify failures by matching English server-message substrings. Playwright and Selenium runtime errors intentionally remain native; do not wrap all exceptions as `AdsPowerError`.

Read `references/troubleshooting.md` when diagnosing a live failure or deciding whether a retry is safe.

## Treat high-impact operations as explicit intent

`browsers.stop_all()`, profile sharing, fingerprint regeneration, kernel download, and application patch updates can affect an installation or many profiles. Do not execute them as a convenient shortcut for an ordinary task.

For live batch/destructive work:

1. Enumerate and resolve the exact targets first.
2. Validate counts/IDs against the user's intent.
3. Execute only the intended mutation.
4. Re-read status/state where the API permits it.

When merely generating code, make the high-impact call visibly intentional and avoid hiding it in generic cleanup.

## Validate before finalizing code

Before returning or committing AdsPower code, check:

- The code targets v3, not a remembered v2/CLI API.
- Sync/async style matches the surrounding application.
- Browser process and adapter ownership are nested correctly.
- "All" operations paginate fully.
- No absolute raw URL or auth propagation can leak the API key.
- Rate limiting is coherent with the number of clients/workers.
- High-impact operations are explicitly justified.
- Exact names/signatures used in fragile code match the current checkout or `inspect_surface.py` output.

For library changes, also run the repository's normal lint/type/test gates rather than treating the skill as a substitute for tests.

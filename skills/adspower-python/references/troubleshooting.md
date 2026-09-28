# Troubleshooting AdsPower Python SDK v3

Load this reference when code fails at runtime, Local API behavior differs from expectations, a browser attachment cannot connect, or a retry strategy is being considered.

Start by identifying the failing layer. Do not immediately rewrite URLs, retry everything, or fall back to raw HTTP.

## 1. Confirm package/source version

If examples disagree with the runtime:

```bash
python skills/adspower-python/scripts/inspect_surface.py
```

The current branch exposes `browsers.start(...) -> BrowserSession` and `browsers.session(...)` as its public alias. The README example using `.session(...)` is valid. Do not use the absence of a separate `def session` in source as evidence that the alias is unavailable.

If working inside the repository, inspect the current method signature directly before assuming the skill's authored-against revision is still current.

## 2. `AdsPowerConfigurationError`

Likely causes:

- malformed `base_url`;
- a path/query/credentials embedded in `base_url`;
- `browser_host` contains a scheme or port;
- invalid browser endpoint policy;
- non-positive timeout.

Fix configuration; do not retry.

## 3. `AdsPowerValidationError`

This indicates caller input violates a public SDK boundary. Inspect the exact operation/model and correct the input. Common examples include wrong page size, both/neither profile selectors, invalid proxy/fingerprint combinations, or a non-numeric group ID.

Do not catch this just to send the same request as raw JSON; that bypasses the guard that found the bug.

## 4. `AdsPowerConnectionError`

Check in order:

1. Is AdsPower running and Local API enabled?
2. Is `ADSPOWER_BASE_URL` / `base_url` reachable from this process/network namespace?
3. If in Docker, can the container reach the host's Local API port?
4. Is DNS/firewall/socket routing failing?

Use `client.health.status()` as a cheap application-level probe after basic TCP reachability is plausible.

Do not change `browser_endpoint_policy` for a failure that occurs before the Local API start request succeeds; API reachability and browser-debugger reachability are different layers.

## 5. `AdsPowerAuthenticationError`

Verify the Local API API key/security configuration and account permissions. The SDK classifies authentication from reliable HTTP 401/403 signals rather than English text.

Never print the key while debugging. Do not append it to CDP or WebDriver URLs.

## 6. `AdsPowerRateLimitError`

First check whether the application is defeating its own rate limiter:

- multiple `AdsPowerClient` instances in one worker;
- multiple processes with independent budgets;
- missing `AdsPowerRatePolicy`;
- a higher-throughput policy than the account/profile-count tier supports.

`AdsPowerRatePolicy` is compliance logic based on documented limits; it cannot predict all server-side enforcement.

For safe reads, use `retry_after` when present and bounded retry. For mutations, reconcile state before repeating: a timeout/429-adjacent failure does not prove that a server-side create/update/delete had no effect.

## 7. `AdsPowerTimeoutError`

Identify which timeout:

- ordinary Local API request timeout;
- browser startup timeout;
- browser version/probe timeout.

A slow browser kernel/profile start should normally change `browser_start_timeout`, not every HTTP timeout. A short debugger probe should stay short enough that a bad endpoint does not stall the whole workflow.

## 8. `AdsPowerProtocolError`

The HTTP exchange succeeded but the response violated the expected Local API shape or typed domain contract.

Investigate version/contract drift:

1. Capture the failing method/path and sanitized response envelope.
2. Compare with `docs/local-api-contract.md` and current contract tests.
3. Check the installed AdsPower patch/version and whether the endpoint/field exists there.
4. If first-party behavior changed, update parser/model/tests; do not paper over it with broad `dict.get()` defaults unless unknown fields are explicitly supported via `extra`.

## 9. `AdsPowerNotFoundError`

This is a convenience lookup miss, not necessarily an HTTP 404. Re-check:

- `profile_id` versus `profile_no`;
- group/name filters;
- whether the object was deleted/moved;
- whether the code only inspected page 1.

Use durable IDs for automation state instead of relying on display names.

## 10. Playwright cannot attach / CDP endpoint is unreachable

The Local API may be healthy while the returned browser endpoint is not reachable from the Python process.

Inspect `session.connection` (without leaking credentials) and ask:

- Is the returned host loopback (`127.0.0.1`/`localhost`) inside the wrong container/VM?
- Is the returned port exposed/routed?
- Does exact mode work on the AdsPower host itself?

Only then try:

```python
AdsPowerClient(
    base_url="http://reachable-api-host:50325",
    browser_endpoint_policy="rewrite_loopback_to_api_host",
)
```

Set `browser_host` when the reachable browser host differs from the API host.

Do not make rewrite mode the global default just because one Docker topology needed it.

## 11. Playwright/Selenium import error

Install only the needed extra:

```bash
pip install 'adspower[playwright]'
pip install 'adspower[selenium]'
# or both
pip install 'adspower[all]'
```

Browser-runtime exceptions remain native. Diagnose Playwright/Selenium errors with those libraries' own exception types after confirming the AdsPower attachment endpoint is valid.

## 12. Endpoint missing from typed SDK

Before using raw access, verify it is genuinely absent from the current resources. Then use a root-relative path:

```python
client.raw.request("POST", "/api/v2/new-endpoint", json={...})
```

If the endpoint is stable and relevant to the library's supported Local API contract, implement a typed resource/model plus contract tests rather than leaving permanent application code on raw dictionaries.

## 13. Cleanup failure after user-code failure

The browser/session adapters are designed not to mask an existing user/control-flow exception with a cleanup exception. Preserve that property in wrappers.

Do not add `finally: stop()` layers that can replace the original exception. Prefer the SDK's nested context managers unless you have an explicit lifecycle reason not to.

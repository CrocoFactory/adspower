# Configuration and networking

The client resolves settings in this order: explicit argument, environment variable, library default.

```python
from adspower import AdsPowerClient

client = AdsPowerClient(
    base_url="http://127.0.0.1:50325",
    api_key="secret",
)
assert client.health.status()
```

Supported networking environment variables are `ADSPOWER_BASE_URL`, `ADSPOWER_API_KEY`,
`ADSPOWER_BROWSER_START_TIMEOUT`, `ADSPOWER_BROWSER_PROBE_TIMEOUT`,
`ADSPOWER_BROWSER_HOST`, and `ADSPOWER_BROWSER_ENDPOINT_POLICY`.

`base_url` must be HTTP(S), contain a host, and contain no credentials, query,
fragment, or base path. `browser_host` is a hostname/IP without scheme, path,
or port. IPv4 and IPv6 are supported.

API keys are excluded from reprs. The Local API Authorization header is never
forwarded to Selenium debugger, CDP, or `/json/version` requests.

## Timeouts

General HTTP and browser-start/probe timeouts are explicit and must be positive.
Transport failures raise `AdsPowerConnectionError`; timeouts raise
`AdsPowerTimeoutError`.

## Docker and remote topology

For Docker Desktop a typical Local API URL is
`http://host.docker.internal:50325`. On Linux the container may need an
explicit host-gateway mapping. The default `browser_endpoint_policy="exact"`
uses AdsPower's returned debugger/CDP endpoints unchanged; this avoids CDP
WebSocket host-header rejections on Local API installations. For a remote or
container topology where those loopback endpoints are not reachable, opt into
`browser_endpoint_policy="rewrite_loopback_to_api_host"` and, when needed,
set `browser_host` to the reachable address.

These are configuration mechanisms, not proof that a particular Docker or
two-host deployment works. Stable release claims require the live topology gate.

## Rate limiting

Rate limiting is client-side and cannot reproduce AdsPower's undisclosed server
algorithm. A global limit and endpoint limits are cumulative and are reserved
together at dispatch. Separate clients/processes do not coordinate unless the
same limiter is shared. Mutating requests are never retried automatically.

```python
from adspower import AdsPowerClient, AdsPowerRatePolicy

client = AdsPowerClient(
    rate_policy=AdsPowerRatePolicy.for_profile_count(profile_count=200),
)
```

`AdsPowerRatePolicy` applies AdsPower's published 1 req/s limits to group and
profile listings, cookies, and user-agent generation. Only configure additional
endpoint-specific values that are supported by first-party/live evidence for the
AdsPower version you run.

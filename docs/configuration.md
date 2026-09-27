# Configuration and networking

**Purpose**: Configure the SDK safely for local, container, and private remote use.

## Endpoint resolution

The client resolves its endpoint in this order:

1. explicit `base_url` argument;
2. `ADSPOWER_BASE_URL` environment variable;
3. `http://127.0.0.1:50325`.

Trailing slashes are removed so paths are joined consistently.

```python
from adspower import AdsPowerClient

client = AdsPowerClient(base_url="http://127.0.0.1:50325/")
assert client.config.base_url == "http://127.0.0.1:50325"
```

The SDK does not perform a `/status` request before every operation. Network
failures are reported from the requested operation. Health checks are explicit:

```python
client.health.check()
```

## Authentication

Pass an API key directly or set `ADSPOWER_API_KEY`. It is attached to every
request as `Authorization: Bearer ...`.

```python
client = AdsPowerClient(api_key="secret")
```

The key is excluded from dataclass output and client `repr`. Avoid logging raw
HTTP request headers in application code.

## Timeouts

The default timeout separates connection, read, write, and pool phases. Browser
startup has its own 60-second default because it is often slower than CRUD.

```python
import httpx

client = AdsPowerClient(
    timeout=httpx.Timeout(connect=5, read=45, write=15, pool=5),
    browser_start_timeout=90,
)

session = client.browsers.start("profile-id", timeout=120)
```

Connection failures raise `AdsPowerConnectionError`; timeouts raise
`AdsPowerTimeoutError`. A non-zero API code raises `AdsPowerAPIError` or a more
specific authentication, rate-limit, or profile-not-found subtype.

## Docker

On Docker Desktop, connect to the host application through:

```bash
ADSPOWER_BASE_URL=http://host.docker.internal:50325
```

Linux Docker may require this Compose configuration:

```yaml
services:
  worker:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Returned Selenium and Playwright endpoints must also be reachable from the
container. The SDK prefers exact endpoints returned by AdsPower and only derives
a Selenium debugger address from `base_url` plus `debug_port` when necessary.

## Private remote hosts

```python
client = AdsPowerClient(
    base_url="http://192.168.1.20:50325",
    api_key="secret",
)
```

Keep the service on a private network or VPN and restrict access with a firewall.
Do not publish the Local API port directly to the internet. Remote browser
attachment also requires AdsPower to return endpoints reachable by the SDK host.

## Rate limiting

Rate limiting is opt-in because current server limits vary by endpoint and
account configuration.

```python
from adspower import AdsPowerClient, RateLimit

client = AdsPowerClient(rate_limit=RateLimit(requests=2, period=1.0))
```

The sync limiter uses a thread lock. The async limiter uses an `asyncio.Lock`, so
concurrent coroutines cannot pass the same timing check simultaneously.

Endpoint-specific policies override the default limiter:

```python
client = AdsPowerClient(
    rate_limit=RateLimit(2, 1.0),
    endpoint_limits={
        "/api/v2/browser-profile/start": RateLimit(1, 1.0),
    },
)
```

## References

- `adspower/config.py`
- `adspower/transport.py`
- `adspower/rate_limit.py`
- `tests/test_v3_client.py`

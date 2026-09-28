# Configuration, models, and network topology

Load this reference when the task involves credentials, environment variables, proxy/fingerprint models, timeouts, or AdsPower running outside the same host/network namespace as the Python process.

## Client configuration precedence

For supported client settings, explicit constructor arguments override environment variables, which override library defaults.

Relevant environment variables:

```text
ADSPOWER_BASE_URL
ADSPOWER_API_KEY
ADSPOWER_BROWSER_START_TIMEOUT
ADSPOWER_BROWSER_PROBE_TIMEOUT
ADSPOWER_BROWSER_HOST
ADSPOWER_BROWSER_ENDPOINT_POLICY
```

Default Local API base URL is `http://127.0.0.1:50325`.

`base_url` must:

- use HTTP or HTTPS;
- include a host;
- contain no embedded username/password;
- contain no query, fragment, or non-root path.

`browser_host` is a hostname or IP only: no scheme, path, query, fragment, or port.

API keys are excluded from client/config reprs. Preserve that behavior in logs and error reporting.

## Browser endpoint policy

Default:

```python
AdsPowerClient(browser_endpoint_policy="exact")
```

Use exact mode when AdsPower and automation can both reach the endpoint AdsPower returns. This is the safest default and avoids modifying CDP URLs unnecessarily.

Use loopback rewriting only for a proven topology mismatch:

```python
AdsPowerClient(
    base_url="http://host.docker.internal:50325",
    browser_endpoint_policy="rewrite_loopback_to_api_host",
)
```

If the API host is not the host that exposes the browser debugger endpoint:

```python
AdsPowerClient(
    base_url="http://adspower-api.internal:50325",
    browser_endpoint_policy="rewrite_loopback_to_api_host",
    browser_host="browser-host.internal",
)
```

Do not copy the Local API Authorization header into Playwright `headers`, Selenium capabilities, or version-probe HTTP requests.

## Timeouts

General HTTP timeout, browser-start timeout, and browser-probe timeout are separate concerns. Use a longer browser-start timeout for slow profile/kernel startup rather than globally inflating every Local API request.

All configured timeout values must be positive.

## Stored proxy model

Use a stored proxy when it should be reusable and independently managed in AdsPower:

```python
from adspower import StoredProxyConfig

proxy = StoredProxyConfig(
    proxy_type="http",
    host="proxy.example",
    port=8080,
    user="username",
    password="password",
    remark="client-a",
)
```

Current stored proxy types: `http`, `https`, `ssh`, `socks5`.

Create returns a tuple of IDs even for one proxy:

```python
proxy_ids = client.proxies.create(proxy)
profile = client.profiles.create(name="client-a", proxyid=proxy_ids[0])
```

## Inline proxy model

Use `InlineProxyConfig` for proxy data owned directly by a profile. Do not turn it into raw JSON yourself.

The model has a `no_proxy()` constructor:

```python
from adspower import InlineProxyConfig

no_proxy = InlineProxyConfig.no_proxy()
```

Normally you do not need to pass that explicitly on profile creation: v3 inserts the supported no-proxy value when both `proxyid` and `user_proxy_config` are absent.

For nontrivial inline proxy providers, inspect the current `InlineProxyConfig` definition before constructing it; `proxy_soft` values are AdsPower-specific and may evolve independently of generic proxy protocol names.

## Fingerprint model

`FingerprintConfig` deliberately exposes Python-friendly typed fields and translates them to AdsPower wire names. Useful examples include:

```python
from adspower import FingerprintConfig, ScreenResolution

fingerprint = FingerprintConfig(
    automatic_timezone=True,
    location_by_ip=True,
    language_by_ip=True,
    screen_resolution=ScreenResolution.fixed(1920, 1080),
    canvas_noise=True,
)
```

Do not copy AdsPower wire keys such as `location_switch` into the Python constructor. The SDK maps wrapper fields to wire fields.

For uncommon settings (WebGL, GPU, media devices, MAC address, TLS, kernel/random-UA combinations), inspect `adspower/models/fingerprint.py` in the current checkout. Those combinations have validation rules that are more important than a long static field list in this skill.

Examples of current validation behavior:

- longitude: -180..180;
- latitude: -90..90;
- geolocation accuracy: 10..5000;
- custom WebGL mode requires WebGL config;
- custom media-device mode requires device counts;
- custom device-name mode requires a device name;
- enabled custom TLS requires a cipher list and a Chrome kernel.

## Platform account

When AdsPower profile metadata includes a platform login, use `PlatformAccount` rather than a loose mapping:

```python
from adspower import PlatformAccount

account = PlatformAccount(
    domain_name="example.com",
    login_user="user@example.com",
)
```

The model requires both domain and login user.

## Profile defaults and validation

Current v3 public validation includes:

- group ID is a numeric string;
- profile name <= 100 characters;
- remark <= 1500 characters;
- country is a lowercase two-letter code;
- at most 30 tag IDs in profile create/update.

Avoid duplicating these validations in application code unless you need earlier domain-specific errors. Let the SDK remain the Local API boundary validator.

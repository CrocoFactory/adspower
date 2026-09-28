# Automation adapters

**Purpose**: Attach Selenium or Playwright safely to a browser started by AdsPower.

## Installation

Automation packages are optional:

```bash
pip install 'adspower[selenium]'
pip install 'adspower[playwright]'
pip install 'adspower[all]'
```

The core client can manage profiles and browser lifecycle without either package.

## Selenium

Start the browser through AdsPower, then attach Selenium:

```python
session = client.browsers.start("profile-id", headless=False)

with session.selenium() as driver:
    driver.get("https://example.com")
```

The adapter uses the debugger address returned by AdsPower. A returned WebDriver
path is used only when that path exists in the Python process filesystem. For a
remote debugger without a locally available driver, the adapter queries
`/json/version` and passes the remote Chromium major version to Selenium
Manager. If that endpoint cannot be reached or does not report a Chromium
version, attachment fails with an instruction to provide a matching
`service=` explicitly. The adapter never starts AdsPower Chromium as an
ordinary Selenium-managed browser.

Headless mode belongs to the AdsPower start request:

```python
session = client.browsers.start("profile-id", headless=True)
```

No `--headless` flag is added to Selenium options after attachment. Automatic
window maximization defaults to false because window geometry can be part of the
profile fingerprint. Page-load strategy is also left at Selenium's default.

```python
with session.selenium(
    start_maximized=True,
    page_load_strategy="eager",
) as driver:
    ...
```

You may pass a configured `selenium.webdriver.ChromeOptions` through `options`.

Custom services and driver options are passed through without being recreated:

```python
from selenium.webdriver.chrome.service import Service

service = Service(port=9515, service_args=["--verbose"])
with session.selenium(
    service=service,
    webdriver_kwargs={},
) as driver:
    ...
```

Use `service_kwargs` when constructing a `Service` object is more convenient.
`service` and `service_kwargs` cannot be supplied together. Firefox attachment
is experimental and should only be used after verifying that the target
AdsPower version returns a real `marionette_port`; select it with
`browser="firefox"`:

```python
session = client.browsers.start(profile_no="42")
with session.selenium(browser="firefox") as driver:
    driver.get("https://example.com")
```

## Sync Playwright

```python
session = client.browsers.start("profile-id")

with session.playwright() as browser:
    context = browser.contexts[0]
    page = context.pages[0]
```

The adapter passes the exact `ws.puppeteer` value returned by AdsPower to
`connect_over_cdp`. It does not reconstruct a `localhost` URL. Because this is an
attach-only flow, the SDK does not call `playwright install chromium` and does not
launch Playwright's bundled browser.

Playwright's CDP attachment applies to Chromium-based browsers and may expose
fewer capabilities than a browser launched directly through Playwright.

The SDK requires Playwright 1.61 or newer because the typed connection options
include `is_local`, `no_defaults` and `artifacts_dir`. Current Playwright
connection options and future options are both supported:

```python
with session.playwright(
    timeout=60_000,
    slow_mo=50,
    no_defaults=True,
    artifacts_dir="artifacts",
    connect_kwargs={"future_option": "value"},
) as browser:
    ...
```

## Async Playwright

```python
session = await client.browsers.start("profile-id")

async with session.playwright() as browser:
    context = browser.contexts[0]
    page = context.pages[0]
    await page.goto("https://example.com")
```

Cleanup order is:

1. disconnect or close the automation connection;
2. request that AdsPower stop the profile;
3. stop the Playwright runtime.

Cleanup methods are idempotent and safe after partial initialization. If user
code raises inside a context manager, a secondary cleanup error is suppressed so
the original exception remains visible. When no user exception exists, cleanup
errors are surfaced.

## Manual lifecycle control

Set `stop_on_exit=False` when multiple adapters or phases use the same session:

```python
session = client.browsers.start("profile-id")

with session.playwright(stop_on_exit=False) as browser:
    ...

session.stop()
```

Always stop sessions in a `finally` block if you do not use automatic cleanup.

## Integration testing

Real automation tests require an AdsPower installation and a dedicated profile.
The repository's integration workflow reads credentials and profile IDs from CI
secrets and is intentionally separate from deterministic mocked contract tests.
Use a local HTTP test server for navigation assertions rather than public sites.

## References

- `adspower/automation.py`
- `adspower/client.py`
- `adspower/async_client.py`
- `tests/test_v3_client.py`

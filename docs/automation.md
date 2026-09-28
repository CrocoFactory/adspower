# Browser automation

Use the outer browser session to own the AdsPower process and an inner adapter
to own the Selenium/Playwright attachment.

```python
with client.browsers.session(profile_id="...") as session:
    with session.selenium() as driver:
        driver.get("https://example.com")
```

Async Playwright follows the same ownership model. Closing the adapter detaches
automation first; closing the session then stops the AdsPower browser.

By default, the SDK uses the debugger and CDP endpoints returned by AdsPower.
For Docker or remote deployments, configure a reachable browser host and use
the endpoint-rewrite policy described in [Configuration](configuration.md).

Firefox attachment must be selected explicitly with `browser="firefox"`.

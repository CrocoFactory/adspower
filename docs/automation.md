# Browser automation

Use the outer browser session to own the AdsPower process and an inner adapter
to own the Selenium/Playwright attachment.

```python
with client.browsers.session(profile_id="...") as session:
    with session.selenium() as driver:
        driver.get("https://example.com")
```

Async Playwright follows the same ownership model. Adapter cleanup happens
before outer-session Local API stop. Cleanup never intentionally masks an
existing user exception, and async cancellation is not translated into an
AdsPower exception.

Topology rewriting is separate from response parsing. Exact mode preserves
returned endpoints. The rewrite policy changes loopback debugger/CDP hosts to
the configured browser host/API host while preserving ports and paths. The
remote Chromium version probe uses a short configurable timeout, follows no
redirects and sends no AdsPower authorization header.

Firefox attachment remains explicit/experimental until verified against a live
target patch; it is never auto-selected from weak response signals.

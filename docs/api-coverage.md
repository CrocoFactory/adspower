# Typed Local API coverage

The v3 client namespaces are identical for sync and async:

`profiles`, `browsers`, `groups`, `proxies`, `categories`, `tags`,
`kernels`, `app`, `health`, and `raw`.

Typed stable coverage is derived from the pinned first-party endpoint registry
documented in [local-api-contract.md](local-api-contract.md). `raw` is the
forward-compatibility escape hatch; it is not a substitute for wrappers for
stable endpoints.

High-impact operations (share, stop-all, fingerprint regeneration, patch
update, kernel download) must be explicitly enabled in live tests.

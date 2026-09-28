# API overview

The synchronous `AdsPowerClient` and asynchronous `AsyncAdsPowerClient` expose
the same resource namespaces:

| Namespace | Use it for |
| --- | --- |
| `profiles` | Profile lifecycle, cookies, user agents and fingerprints |
| `browsers` | Browser start/stop, status and automation sessions |
| `groups` | Profile groups |
| `proxies` | Stored proxy configurations |
| `categories` | Extension categories |
| `tags` | Browser profile tags |
| `kernels` | Browser kernel information and downloads |
| `app` | AdsPower application updates |
| `health` | Local API availability |
| `raw` | Root-relative requests to Local API endpoints not yet wrapped by the SDK |

Use the typed namespaces for common operations. `raw` is useful when you need a
new Local API endpoint before it appears in a typed release.

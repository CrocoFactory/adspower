# Local API reference

This reference lists the Local API operations available through the SDK. For
field-level details, consult the [AdsPower Local API documentation](https://localapi-doc-en.adspower.com/).

| SDK operation | Method and path | Notes |
| --- | --- | --- |
| `health.status` | GET `/status` | Local API availability |
| `categories.list` | GET `/api/v2/category/list` | Page size 1–100 |
| `profiles.create`, `update`, `delete_many` | POST profile endpoints | Profile configuration and lifecycle |
| `profiles.list` | POST `/api/v2/browser-profile/list` | Page size 1–100; supports name and tag filters |
| `profiles.move`, `cookies`, `user_agents` | Profile endpoints | Move profiles and retrieve profile data |
| `profiles.new_fingerprint`, `delete_cache`, `share` | Profile endpoints | Profile maintenance and sharing |
| `browsers.start`, `stop`, `status` | Browser profile endpoints | Browser lifecycle and connection details |
| `browsers.list_opened`, `cloud_status` | Browser endpoints | Opened local and cloud browser status |
| `browsers.stop_all` | POST `/api/v2/browser-profile/stop-all` | Stops all local browser profiles |
| `groups.create`, `update`, `list` | Group endpoints | Group page size up to 2000 |
| `proxies.create_many`, `update`, `list`, `delete_many` | Proxy endpoints | Create up to 500 proxies per request |
| `tags.create`, `update`, `list`, `delete` | Tag endpoints | Tag page size up to 200 |
| `kernels.list`, `download` | Kernel endpoints | Available browser kernels and downloads |
| `app.update_patch` | POST `/api/v2/browser-profile/update-patch` | AdsPower application update |

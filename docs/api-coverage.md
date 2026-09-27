# API coverage

The SDK exposes typed, forward-compatible wrappers for the current Local API.
Unknown response fields are retained in model `extra` dictionaries and unknown
request fields can be passed through keyword arguments or `client.request()`.

| Operation | Endpoint | Sync | Async | Notes |
| --- | --- | :---: | :---: | --- |
| Profile create/update/list/delete | `/api/v2/browser-profile/*` | yes | yes | IDs, numbers, pagination, future fields |
| Profile batch delete | `/api/v2/browser-profile/delete` | yes | yes | maximum 100 |
| Profile regroup | `/api/v1/user/regroup` | yes | yes | explicit profile ID list |
| Profile cache deletion | `/api/v2/browser-profile/delete-cache` | yes | yes | cache type list is passed through |
| Profile cookies | `/api/v2/browser-profile/cookies` | yes | yes | string JSON normalized to a list |
| Share profile | `/api/v2/browser-profile/share` | yes | yes | maximum 200 profiles |
| Browser start/stop | `/api/v2/browser-profile/{start,stop}` | yes | yes | profile ID or number |
| Browser status | `/api/v2/browser-profile/active` | yes | yes | `BrowserStatus.active` convenience property |
| Local active browsers | `/api/v1/browser/local-active` | yes | yes | `RunningBrowser` models |
| Groups | `/api/v1/group/*` | yes | yes | list page size up to 2000 |
| Proxy create/update/list/delete | `/api/v2/proxy-list/*` | yes | yes | delete/list IDs validated to 100 |
| Categories | `/api/v2/category/list` | yes | yes | page size up to 100 |
| Health | `/status` | yes | yes | explicit check only |
| Raw Local API | any relative `/...` path | yes | yes | `unwrap=False` preserves response envelope |

## Deliberate limitations

- Playwright attaches through CDP, so it has lower fidelity than a native
  Playwright-launched browser.
- Firefox attachment requires AdsPower to return a usable `marionette_port` and
  a driver topology available to the Python process.
- Real AdsPower, Docker, and remote-host integration tests are separate from
  deterministic mock contract tests and require explicit environment setup.

# AdsPower Local API contract used by SDK v3

The typed v3 surface is pinned to first-party contract commit
`AdsPower/adspower-browser@06dc59d65e094365139134d22e8eacb95ebedd62`.
Live fixtures from the target AdsPower patch take precedence when they disagree.

| SDK namespace | Method/path | Request location | Verified notes |
|---|---|---|---|
| health.status | GET `/status` | none | first-party contract |
| categories.list | GET `/api/v2/category/list` | query | `category_id/page/limit` |
| profiles.create | POST `/api/v2/browser-profile/create` | body | no-proxy config is injected only when neither proxy form is supplied |
| profiles.update | POST `/api/v2/browser-profile/update` | body | mutation returns no synthetic Profile |
| profiles.list | POST `/api/v2/browser-profile/list` | body | `limit` 1–200; name/tag filters supported; pagination metadata retained |
| profiles.delete_many | POST `/api/v2/browser-profile/delete` | body | profile id array |
| profiles.move | POST `/api/v1/user/regroup` | body | group + user ids |
| profiles.cookies | GET `/api/v2/browser-profile/cookies` | query | one selector |
| profiles.user_agents | POST `/api/v2/browser-profile/ua` | body | max 10 |
| profiles.new_fingerprint | POST `/api/v2/browser-profile/new-fingerprint` | body | max 10; live destructive gate required |
| profiles.delete_cache | POST `/api/v2/browser-profile/delete-cache` | body | cache-type array |
| profiles.share | POST `/api/v2/browser-profile/share` | body | max 200; live destructive gate required |
| browsers.start | POST `/api/v2/browser-profile/start` | body | typed start options; omitted bools preserve server defaults |
| browsers.stop | POST `/api/v2/browser-profile/stop` | body | one selector |
| browsers.stop_all | POST `/api/v2/browser-profile/stop-all` | body | live destructive gate required |
| browsers.status | GET `/api/v2/browser-profile/active` | query | endpoint parsing separated from topology resolution |
| browsers.list_opened | GET `/api/v1/browser/local-active` | none | local opened list |
| browsers.cloud_status | POST `/api/v1/browser/cloud-active` | body | max 100 ids |
| groups.create/update/list | POST/POST/GET | body/body/query | first-party contract |
| proxies.create/update/list/delete | POST | body | create body is an array; list limit 1–200; delete max 100 |
| tags.list/create/update/delete | POST | body | list limit 1–200; list ids max 100 |
| kernels.list | GET `/api/v2/browser-profile/kernels` | query | Chrome/Firefox |
| kernels.download | POST `/api/v2/browser-profile/download-kernel` | body | live high-impact gate required |
| app.update_patch | POST `/api/v2/browser-profile/update-patch` | body | stable/beta; live high-impact gate required |

Source files at the pinned first-party commit:
`packages/core/src/constants/localApiContracts.ts`,
`skills/adspower-browser/references/browser-profile-management.md`,
`fingerprint-config.md`, `user-proxy-config.md`, `proxy-management.md`,
`browser-tag-management.md`, `browser-kernel-management.md`, and
`client-patch-management.md`.

The SDK does not claim unverified Firefox, Docker, remote-host, rate-limit,
batch-limit, or client-patch behavior from mocks alone. Release claims require
the live integration gates.

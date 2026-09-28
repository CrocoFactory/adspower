# AdsPower Local API contract used by SDK v3

The typed v3 surface is pinned to first-party contract commit
`AdsPower/adspower-browser@06dc59d65e094365139134d22e8eacb95ebedd62`.

Evidence precedence is:

1. live request/response fixtures from the target AdsPower patch;
2. the pinned first-party repository;
3. official Local API documentation;
4. historical SDK behavior.

A typed wrapper must not claim behavior that is unsupported by those sources.
At the time of this refactor, the request contracts below are pinned to the
first-party commit; target-patch live verification remains a release gate rather
than something inferred from mocks.

| SDK operation | Method/path | Request | Verified contract notes | Live status |
| --- | --- | --- | --- | --- |
| health.status | GET `/status` | none | availability | release-gated |
| categories.list | GET `/api/v2/category/list` | query | `category_id`, page, limit 1–100 | release-gated |
| profiles.create | POST `/api/v2/browser-profile/create` | body | typed profile/proxy/fingerprint fields; no-proxy fallback only | release-gated |
| profiles.update | POST `/api/v2/browser-profile/update` | body | mutation returns no synthetic Profile | release-gated |
| profiles.list | POST `/api/v2/browser-profile/list` | body | limit 1–200; name/tag filters; pagination metadata | release-gated |
| profiles.delete_many | POST `/api/v2/browser-profile/delete` | body | profile id array | release-gated |
| profiles.move | POST `/api/v1/user/regroup` | body | group + user ids | release-gated |
| profiles.cookies | GET `/api/v2/browser-profile/cookies` | query | one selector | release-gated |
| profiles.user_agents | POST `/api/v2/browser-profile/ua` | body | max 10 | release-gated |
| profiles.new_fingerprint | POST `/api/v2/browser-profile/new-fingerprint` | body | max 10; high-impact gate | high-impact gate |
| profiles.delete_cache | POST `/api/v2/browser-profile/delete-cache` | body | documented cache-type array | release-gated |
| profiles.share | POST `/api/v2/browser-profile/share` | body | max 200; high-impact gate | high-impact gate |
| browsers.start | POST `/api/v2/browser-profile/start` | body | typed optional start fields; omitted booleans preserve defaults | release-gated |
| browsers.stop | POST `/api/v2/browser-profile/stop` | body | one selector | release-gated |
| browsers.stop_all | POST `/api/v2/browser-profile/stop-all` | body | no parameters | high-impact gate |
| browsers.status | GET `/api/v2/browser-profile/active` | query | one selector | release-gated |
| browsers.list_opened | GET `/api/v1/browser/local-active` | none | opened local browsers | release-gated |
| browsers.cloud_status | POST `/api/v1/browser/cloud-active` | body | max 100 comma-separated user ids | release-gated |
| groups.create | POST `/api/v1/group/create` | body | group_name + optional remark | release-gated |
| groups.update | POST `/api/v1/group/update` | body | numeric group_id + group_name | release-gated |
| groups.list | GET `/api/v1/group/list` | query | page_size max 100, default 10 | release-gated |
| proxies.create_many | POST `/api/v2/proxy-list/create` | array body | no batch cap invented; proxy port contract 0–65536 | release-gated |
| proxies.update | POST `/api/v2/proxy-list/update` | body | typed proxy fields | release-gated |
| proxies.list | POST `/api/v2/proxy-list/list` | body | limit 1–200, default 50 | release-gated |
| proxies.delete_many | POST `/api/v2/proxy-list/delete` | body | max 100 ids | release-gated |
| tags.list | POST `/api/v2/browser-tags/list` | body | limit 1–200; ids max 100 | release-gated |
| tags.create/update/delete | POST tag endpoints | body | typed tag payloads | release-gated |
| kernels.list | GET `/api/v2/browser-profile/kernels` | query | Chrome/Firefox | release-gated |
| kernels.download | POST `/api/v2/browser-profile/download-kernel` | body | high-impact | high-impact gate |
| app.update_patch | POST `/api/v2/browser-profile/update-patch` | body | stable/beta | high-impact gate |

Pinned source files include:
`packages/core/src/constants/localApiContracts.ts`,
`packages/core/src/types/schemas.ts`,
`skills/adspower-browser/references/browser-profile-management.md`,
`application-management.md`, `group-management.md`, `fingerprint-config.md`,
`browser-kernel-config.md`, `user-proxy-config.md`, `proxy-management.md`,
`browser-tag-management.md`, `browser-kernel-management.md`, and
`client-patch-management.md`.

The minimum AdsPower patch for a stable v3 release must be set from the actual
target-patch live matrix. The SDK deliberately does not manufacture that value
from mocked tests or from the newest field version mentioned in reference docs.

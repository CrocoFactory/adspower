# Migrating from 2.x to 3.x

v3 is a clean major version and intentionally has no compatibility layer.

Key changes:

- instantiate `AdsPowerClient` or `AsyncAdsPowerClient`;
- use resource namespaces such as `client.profiles` and `client.browsers`;
- profile creation returns `CreatedProfile`, not a partial `Profile`;
- updates return `None`; call `get()` explicitly if a fresh snapshot is needed;
- list methods return `Page[T]` and preserve pagination metadata;
- use canonical `profile_id`, `profile_no`, and `proxy_type` names;
- use Python booleans/config dataclasses; wire `"0"/"1"` values are internal;
- raw access moved to `client.raw.request(...)`;
- catch the canonical `AdsPower...` exception hierarchy only;
- browser process lifecycle belongs to `BrowserSession`; adapters only attach/detach.

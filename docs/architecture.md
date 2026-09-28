# SDK behavior

The SDK separates Local API access from browser automation. Resource methods
manage AdsPower data, while a `BrowserSession` manages one browser process and
automation adapters attach to that process.

Profile, proxy and tag methods return typed Python values. Unknown fields from
AdsPower responses are preserved in `extra`, so applications can access newer
server fields without losing the known data model.

Write operations do not perform hidden follow-up reads or automatic retries.
If you need the latest profile data after an update, request it explicitly with
`client.profiles.get(profile_id)`.

# AdsPower SDK documentation

This index separates user workflows from implementation and release guidance so
each topic can be read independently.

## User guides

- [Configuration and networking](configuration.md) — endpoint resolution,
  authentication, timeouts, Docker, remote hosts, and rate limiting.
- [Profiles and browser sessions](profiles-and-sessions.md) — V2 profile CRUD,
  tolerant response models, groups, and browser lifecycle.
- [Automation adapters](automation.md) — Selenium and Playwright attachment,
  endpoint selection, cleanup, and optional dependencies.
- [API coverage](api-coverage.md) — supported Local API operations, endpoints,
  sync/async parity, and deliberate limitations.
- [Migration from 2.x to 3.x](migration-2-to-3.md) — breaking changes and direct
  replacements for the old class-level APIs.

## Maintainer guide

- [Development and release checks](development.md) — architecture, tests, CI,
  integration requirements, dependency matrices, and release gates.

## Source map

| Area | Main implementation |
| --- | --- |
| Configuration | `adspower/config.py` |
| Sync/async transport | `adspower/transport.py` |
| Models | `adspower/models.py` |
| V2 and group APIs | `adspower/api.py` |
| Sync client and sessions | `adspower/client.py` |
| Async client and sessions | `adspower/async_client.py` |
| Browser adapters | `adspower/automation.py` |
| Rate limiting | `adspower/rate_limit.py` |
| Exception hierarchy | `adspower/exceptions.py` |

The original modernization plan is an implementation input and is intentionally
not part of the tracked documentation set.

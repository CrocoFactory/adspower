# AdsPower SDK v3 documentation

## User guides

- [Configuration and networking](configuration.md)
- [Profiles and browser sessions](profiles-and-sessions.md)
- [Automation](automation.md)
- [Errors](errors.md)
- [Typed API coverage](api-coverage.md)
- [Local API contract](local-api-contract.md)
- [Migration from 2.x](migration-2-to-3.md)

## Maintainer guide

- [Architecture](architecture.md)
- [Development and release checks](development.md)

## Source map

| Area | Implementation |
| --- | --- |
| Configuration | `adspower/config.py` |
| Sync/async clients | `adspower/client.py`, `adspower/async_client.py` |
| HTTP transport | `adspower/transport/` |
| Local API protocol | `adspower/protocol.py` |
| Endpoint registry | `adspower/_contracts.py` |
| Resource serializers | `adspower/resources/` |
| Domain/config models | `adspower/models/` |
| Automation adapters | `adspower/automation/` |
| Rate limiting | `adspower/rate_limit.py` |
| Errors | `adspower/errors.py` |

v3 intentionally has no compatibility layer for intermediate v3 branch APIs.

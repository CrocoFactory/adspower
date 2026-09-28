# v3 architecture

v3 separates concerns deliberately.

- `transport/`: HTTPX I/O, authorization header, timeout translation and the client-side limiter. It returns `httpx.Response`.
- `protocol.py`: JSON decoding, Local API envelope validation and reliable HTTP/business error mapping.
- `resources/`: endpoint request serialization plus domain parsing. Sync/async methods use the same helpers and endpoint registry.
- `models/`: immutable result/config values with strict parsing of known fields and typed `extra` metadata.
- `automation/`: Selenium/Playwright attachment only. `BrowserSession` owns AdsPower start/stop.
- `_contracts.py`: single method/path source for every typed endpoint.
- `client.raw`: forward-compatible access to a root-relative Local API path and returns `AdsPowerEnvelope`.

Mutations never hide follow-up GETs and writes are never automatically retried.
Malformed successful responses are protocol errors rather than API errors.

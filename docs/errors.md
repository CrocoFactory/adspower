# Errors

```text
AdsPowerError
├── AdsPowerValidationError
├── AdsPowerConfigurationError
├── AdsPowerTransportError
│   ├── AdsPowerConnectionError
│   └── AdsPowerTimeoutError
├── AdsPowerAPIError
│   ├── AdsPowerAuthenticationError
│   └── AdsPowerRateLimitError
├── AdsPowerProtocolError
└── AdsPowerNotFoundError
```

Authentication is classified from reliable HTTP 401/403 signals, rate limiting
from HTTP 429, and other business-envelope failures remain
`AdsPowerAPIError`. The SDK never classifies errors by English message
substrings. A successful transport with malformed JSON/envelope/domain fields
raises `AdsPowerProtocolError`. Convenience lookup misses raise
`AdsPowerNotFoundError`. Native Selenium/Playwright runtime errors stay native.

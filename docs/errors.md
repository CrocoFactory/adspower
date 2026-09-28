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

`AdsPowerAuthenticationError` represents HTTP 401/403 responses and
`AdsPowerRateLimitError` represents HTTP 429. Other Local API failures raise
`AdsPowerAPIError`.

`AdsPowerProtocolError` means a response could not be interpreted as the
expected Local API data. `AdsPowerNotFoundError` is raised by convenience lookup
methods when no matching resource exists. Selenium and Playwright errors remain
their native exception types.

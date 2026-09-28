# Development and release checks

**Purpose**: Describe the 3.x architecture and the evidence required before publishing a release.

## Architecture

The implementation keeps shared behavior outside sync and async wrappers:

- `config.py` resolves endpoint, authentication, and timeouts;
- `models.py` contains tolerant domain and connection models;
- `api.py` owns endpoint paths and serialization;
- `transport.py` owns HTTPX I/O and response/error handling;
- `rate_limit.py` provides concurrency-safe limiters;
- `client.py` and `async_client.py` compose public services;
- `automation.py` contains optional browser adapters;
- `api.py` contains V2 profile/browser operations and the V1 group endpoints
  that remain part of the current AdsPower contract.
- `security.py` provides recursive redaction for model representations and
  diagnostics.

The transport uses only public HTTPX APIs. A request is sent directly, without a
status preflight. HTTP errors, network errors, JSON failures, and AdsPower
business errors are normalized at this boundary.

## Local checks

```bash
poetry install --all-extras
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest -m "not integration" --cov=adspower
poetry build
poetry run twine check dist/*
```

Unit and contract tests use `httpx.MockTransport`; they must not require a running
AdsPower process or external internet access.

## Test layers

Core tests cover:

- configuration precedence and secret redaction;
- exact V2 paths, HTTP methods, headers, and request JSON;
- V1 namespace routing;
- tolerant parsing and `user_proxy_config` regression;
- custom, Docker-style, and remote base URLs;
- explicit health checks with no automatic preflight;
- authentication, rate-limit, API, HTTP, and network errors;
- sync/async semantic parity;
- concurrency-safe rate limiting;
- exact Playwright CDP and Selenium debugger endpoints;
- idempotent cleanup and preservation of user exceptions;
- package build and import smoke checks.

Anonymized API responses belong under `tests/fixtures/v1` and
`tests/fixtures/v2`. Add a fixture whenever AdsPower changes a response shape.

## Real integration tests

Release candidates that advertise browser automation must also run on a trusted,
self-hosted environment with:

```bash
ADSPOWER_INTEGRATION=1
ADSPOWER_BASE_URL=...
ADSPOWER_API_KEY=...
ADSPOWER_TEST_PROFILE_ID=...
```

The suite creates and deletes its own profile for CRUD, cookie, cache, group-list,
and category-list coverage. Real proxy CRUD additionally requires
`ADSPOWER_TEST_PROXY_HOST` and `ADSPOWER_TEST_PROXY_PORT`; type and credentials
use the corresponding optional `ADSPOWER_TEST_PROXY_*` variables. All created
profiles and proxies are deleted in `finally` blocks.
The release workflow sets `ADSPOWER_REQUIRE_PROXY_INTEGRATION=1`, turning
missing proxy settings into a failure instead of a skip.

The Selenium test must navigate a local deterministic page, read the DOM, execute
JavaScript, manage tabs, disconnect, stop the profile, and repeat stop safely.

Sync and async Playwright integration currently cover the happy-path attach,
navigation, page lifecycle, disconnect, and stop flow. Already-closed,
connection-loss, and cancellation behavior has deterministic mocked regression
coverage; it must be promoted to the live gate before those live failure modes
are claimed as verified.

Docker and two-host remote topology remain explicit manual release gates until
dedicated runners are provisioned. Mocked endpoint rewriting is contract
coverage, not proof of network topology.

## Compatibility matrix

CI covers Python 3.10 through 3.15. Stable release jobs are blocking once that
Python version is generally available; prerelease interpreters may be allowed to
fail until then.

Dependency jobs install:

1. the minimum declared HTTPX, Selenium, Playwright, and typing-extensions;
2. the latest versions within supported major ranges;
3. optional prereleases in a non-blocking scheduled job.

Future Selenium 5 or Playwright 2 support requires a dedicated branch and full
integration suite before dependency ranges are widened.

## Packaging

Build both wheel and source distribution. In a clean environment, test:

```text
core install and import
[selenium] install and import
[playwright] install and import
[all] install and import
pip check
```

Run package smoke tests across the supported Python matrix. Documentation code
samples should be compiled or executed with mocked transport where practical.

The CI package job uploads the checked wheel and source distribution as a build
artifact. Publishing to PyPI is intentionally not automated yet; configure a
protected GitHub environment and PyPI trusted publishing before adding a release
deployment job.

## Release gate

Do not publish based only on unit tests. The release candidate gate is:

1. lint and formatting;
2. type checks;
3. unit and mocked HTTP contracts;
4. minimum and latest dependency matrices;
5. Python-version matrix;
6. real Selenium happy-path integration;
7. real sync and async Playwright happy-path integration;
8. manual Docker/two-host topology verification when those deployment modes are advertised;
9. package build/install smoke tests;
10. deterministic failure-mode/resource-warning lifecycle checks.

Remote-host integration can be a documented manual or self-hosted gate when CI
cannot provision the topology. Every fixed regression must retain an automated
test in the repository.

The integration workflow also runs for `v*` tags, so an available self-hosted
AdsPower runner and a successful live suite are release conditions. Docker and
private two-host claims still require runners carrying those actual topologies;
mock endpoint rewriting is not accepted as integration evidence.

## References

- `.github/workflows/ci.yml`
- `.github/workflows/nightly.yml`
- `pyproject.toml`
- `tests/test_v3_client.py`

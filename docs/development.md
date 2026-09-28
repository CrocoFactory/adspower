# Development and release checks

## Architecture

- `transport/`: HTTP I/O, authentication, timeout translation and client-side limiter.
- `protocol.py`: JSON/envelope validation and stable error classification.
- `resources/`: request serialization and resource parsing.
- `models/`: immutable result/config models and strict known-field parsing.
- `automation/`: Selenium/Playwright attachment and endpoint resolution.
- `_contracts.py`: one method/path definition for each typed endpoint.

Sync and async implementations share endpoint definitions, validators,
serializers, parsers, and result models. They differ only in I/O mechanics.

## Required local checks

```bash
poetry install --all-extras
poetry run ruff check adspower tests
poetry run ruff format --check adspower tests
poetry run pyright adspower
poetry run pytest -m "not integration" --cov=adspower --cov-report=term-missing --cov-fail-under=90
poetry build
poetry run twine check dist/*
```

The CI matrix also checks supported Python versions, minimum/latest automation
dependencies, clean wheel installs for core/`selenium`/`playwright`/`all`,
`pip check`, and `py.typed`.

## Live release gates

Mocks are contract coverage, not topology evidence. Before a stable v3 release,
run the self-hosted integration suite against the target AdsPower patch,
including local Selenium, sync Playwright and async Playwright.

High-impact operations (share, stop-all, fingerprint regeneration, patch
update, kernel download) require a dedicated opt-in environment flag and
disposable/test-safe resources. Docker and a real two-host remote topology must
be exercised before those deployment modes are advertised as verified. Firefox
remains experimental until a live gate verifies it.

The pinned first-party contract is
`AdsPower/adspower-browser@06dc59d65e094365139134d22e8eacb95ebedd62`.
When a live fixture disagrees with that source, the fixture wins and the
contract document and regression test must be updated together.

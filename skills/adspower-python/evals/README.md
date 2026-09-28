# Trigger evals

Use `trigger-cases.json` to test the `description` metadata independently of output quality.

Expected behavior:

- Every `positive` prompt should activate `adspower-python` when the skill is available.
- Every `negative` prompt should stay inactive unless the surrounding conversation/repository context independently establishes that the CrocoFactory/adspower v3 Python SDK is in use.

When refining the description, keep difficult near-misses. Do not make the description so broad that any mention of AdsPower, Playwright, Selenium, browser profiles, or Python triggers the skill.

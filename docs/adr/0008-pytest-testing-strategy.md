# ADR-0008 — Testing with pytest; run in CI, not on every commit

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

The backend needs an automated test suite and a clear policy on where tests run.
Two questions: which framework, and at which gate (pre-commit vs CI).

Running the full suite on every `git commit` (a pre-commit hook) makes commits
slow as the suite grows and discourages small, frequent commits. The fast static
checks (ruff, import-linter, basedpyright) are cheap enough to keep on commit;
tests are not.

## Decision

- **pytest** is the test framework, with **pytest-asyncio** (`asyncio_mode = "auto"`)
  for async tests (Pydantic AI agents are async) and **httpx** for FastAPI's
  `TestClient`. Configured in `backend/pyproject.toml` under
  `[tool.pytest.ini_options]`; tests live in `backend/tests/`.
- **Tests run in CI** (a dedicated `tests` job in `.github/workflows/ci.yml`) on
  every push to `main` and every PR.
- **Tests are NOT a pre-commit hook** — local commits stay fast. The fast static
  checks remain on commit; CI is the gate that runs the suite.
- Test naming convention: `test_{unit}_should_{expected}_when_{condition}`.
- Slow/external tests are marked `@pytest.mark.integration` and can be excluded
  locally with `-m "not integration"`.

## Consequences

**Positive**

- Fast local commits; the full suite is still enforced before merge via CI.
- Async-ready and FastAPI-ready from the start.
- `--strict-markers` prevents typos in marker names from silently passing.

**Negative / trade-offs**

- A failing test is caught in CI rather than at commit time, so a contributor can
  create a local commit that CI later rejects. This is the deliberate trade for
  commit speed; run `uv run pytest` before pushing.
- Tests live outside `app/`, so they are not covered by the import-linter
  contracts or the basedpyright `include` (both scoped to `app`).

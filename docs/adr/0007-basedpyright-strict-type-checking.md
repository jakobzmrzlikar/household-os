# ADR-0007 — basedpyright for strict backend type checking

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

The backend convention requires type hints on all function parameters and return
values (CLAUDE.md). Hints are only valuable if a checker enforces them. We need a
static type checker for the Python backend.

Options considered: **mypy**, **pyright**, and **basedpyright** (a pyright fork
with stricter defaults, additional rules, and a baseline feature for adopting
strict checks on existing code). A prior backend used basedpyright successfully.

## Decision

Use **basedpyright** in **strict** mode for the backend.

- Configured in `backend/pyproject.toml` under `[tool.basedpyright]`:
  `typeCheckingMode = "strict"`, `include = ["app"]`, and `pythonVersion` set to
  match the project's pinned Python (`backend/.python-version`).
- Run via `uv run basedpyright` from `backend/`, and enforced by a `basedpyright`
  pre-commit hook (ADR-0004 toolchain).
- The codebase starts at **zero errors under strict**, so no baseline is used.
  New type errors must be fixed, not silenced. If a one-time baseline is ever
  needed (e.g. a large import), generate it with
  `uv run basedpyright --writebaseline` so only *new* errors fail the build.

## Consequences

**Positive**

- Type hints are mechanically enforced; type regressions fail before merge.
- Strict mode from day one avoids accumulating an untyped legacy to migrate later.
- Pairs with the hexagonal boundaries (ADR-0005): typed ports/Protocols are
  checked, so adapter implementations must satisfy their port contracts.

**Negative / trade-offs**

- Strict basedpyright is stricter than pyright/mypy defaults and can flag
  third-party libraries with weak stubs; such cases are handled per-rule rather
  than by lowering the global mode.
- basedpyright runs on a bundled Node runtime (`nodejs-wheel-binaries`), adding
  to the dev environment size.

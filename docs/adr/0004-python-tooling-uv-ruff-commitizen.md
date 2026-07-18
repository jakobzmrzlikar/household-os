# ADR-0004 — Python tooling: uv, ruff, commitizen + pre-commit

- **Status:** Accepted
- **Date:** 2026-06-24

## Context

The sol backend (FastAPI + Pydantic AI, ADR-0003) needs dependency management,
linting/formatting, and a commit convention. The project is solo-developed in a
monorepo (ADR-0001), so the toolchain should be fast, low-ceremony, and
enforceable automatically rather than by discipline.

The same stack — uv, ruff, commitizen — was used successfully in a prior project
and is carried over here.

## Decision

Adopt for the Python backend:

- **uv** — dependency and environment management. The backend is an application
  (`[tool.uv] package = false`); dependencies are pinned in `backend/uv.lock`.
- **ruff** — linting and formatting, configured in `backend/pyproject.toml`.
- **commitizen** — enforce **Conventional Commits** and drive version bumping.

Enforce them with **pre-commit** at the repo root:

- `uv-lock` scoped to the backend project (`args: [--project, backend]`).
- `ruff-check --fix` then `ruff-format` (lint before format).
- `commitizen` on the `commit-msg` stage to validate every commit message.

Conventional Commits apply repo-wide (frontend commits included), since
commit-message validation is a repo-level concern.

### Monorepo adaptations from the source config

- The Python project lives in `backend/`, so `uv-lock` is pointed there and
  ruff discovers config from `backend/pyproject.toml`.
- The upstream project's `check-adr-numbering` local hook (referencing
  `scripts/check_adr_numbering.py` and `docs/explanation/adr/`) was **not**
  carried over — our ADRs live in `docs/adr/` with a `README.md` index and no
  such script exists yet. It can be ported later if ADR hygiene needs enforcing.

## Consequences

**Positive**

- Fast, reproducible installs (uv) and one fast tool for lint+format (ruff).
- Commit history is machine-readable; version bumps and changelogs can be
  automated from it.
- Quality gates run automatically on commit, not by memory.

**Negative / trade-offs**

- Contributors must run `pre-commit install` (and `--hook-type commit-msg`)
  once per clone; the commit-msg hook is easy to forget.
- Pinned hook revs (`uv-pre-commit`, `ruff-pre-commit`, `commitizen`) need
  periodic bumping and should track the versions used in CI.

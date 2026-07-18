# ADR-0001 — Monorepo for frontend + backend

- **Status:** Accepted
- **Date:** 2026-06-24

## Context

sol consists of (at least) a React frontend and a FastAPI/Pydantic backend, and
will likely grow shared concerns over time — TypeScript types mirrored from
Pydantic models, a shared design system, deployment and tooling config.

The project is solo-developed. The main early cost of multiple repos is the
friction of coordinating changes that span the frontend/backend boundary: a
single feature (e.g. a new endpoint plus its UI) requires two PRs, two review
cycles, and version coordination between repos. For a solo developer this is
pure overhead with little compensating benefit.

## Decision

Keep the frontend and backend in a single monorepo.

- One repository, one source of truth, one place to clone and set up.
- Cross-cutting changes land atomically in a single commit/PR — an API change
  and its consumer move together, so `main` is never internally inconsistent.
- Defer splitting into multiple repos until there is concrete, felt pain
  (e.g. independent deploy cadences, separate teams, or CI times that demand
  isolation). We split in response to evidence, not in anticipation.

## Consequences

**Positive**

- Atomic cross-cutting changes; no inter-repo version dance.
- Single setup, single CI configuration, shared tooling and config.
- Easier to share code/types across the boundary as the project grows.

**Negative / trade-offs**

- CI must be scoped per-package as the repo grows to avoid rebuilding/testing
  everything on every change.
- Tooling has to accommodate a mixed-language layout (Node/TypeScript +
  Python).
- A future split, if needed, carries history-extraction cost — accepted as a
  deliberately deferred risk.

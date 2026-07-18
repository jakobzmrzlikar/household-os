# Architecture Decision Records

This directory records the significant architectural decisions for
**household-os**.

We use lightweight ADRs (one Markdown file per decision). Each record captures
the context, the decision, and the consequences at the time it was made. ADRs
are immutable once accepted — when a decision changes, add a new ADR that
supersedes the old one rather than editing history.

## Format

Each ADR follows this structure:

- **Status** — Proposed | Accepted | Superseded by ADR-XXXX
- **Context** — the forces at play and why a decision was needed
- **Decision** — what we chose to do
- **Consequences** — the resulting trade-offs, good and bad

File naming: `NNNN-short-title.md` (zero-padded, monotonically increasing).

## Index

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-monorepo-for-frontend-and-backend.md) | Monorepo for frontend + backend | Accepted |
| [0002](0002-claude-design-for-component-library.md) | Claude Design + design-sync for the component library | Accepted |
| [0003](0003-pydantic-ai-as-agent-framework.md) | Pydantic AI as the agent framework | Accepted |
| [0004](0004-python-tooling-uv-ruff-commitizen.md) | Python tooling: uv, ruff, commitizen + pre-commit | Accepted |
| [0005](0005-hexagonal-architecture-backend.md) | Hexagonal architecture (ports & adapters) for the backend | Accepted |
| [0006](0006-attrs-over-pydantic-and-dataclasses.md) | attrs by default; pydantic at boundaries; never dataclasses | Accepted |
| [0007](0007-basedpyright-strict-type-checking.md) | basedpyright for strict backend type checking | Accepted |
| [0008](0008-pytest-testing-strategy.md) | Testing with pytest; run in CI, not on every commit | Accepted |
| [0009](0009-dependency-injector-for-composition-root.md) | dependency-injector for the composition root | Accepted |

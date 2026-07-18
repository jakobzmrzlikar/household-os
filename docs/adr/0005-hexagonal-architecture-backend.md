# ADR-0005 — Hexagonal architecture (ports & adapters) for the backend

- **Status:** Accepted
- **Date:** 2026-06-24

## Context

The sol backend (FastAPI + Pydantic AI + SQLAlchemy/Alembic, ADR-0003/ADR-0004)
will accumulate agent logic, persistence, and external integrations (LLM
providers, travel APIs). Without an enforced structure, framework details
(FastAPI, SQLAlchemy, provider SDKs) tend to leak into business logic, making the
core hard to test in isolation and hard to change.

A prior backend used **Hexagonal Architecture** (Ports & Adapters) successfully.
We adopt it here **strictly** — not as a loose suggestion but as an enforced
boundary.

## Decision

Structure `backend/app/` as concentric layers with dependencies pointing
**inward only**:

```
backend/app/
  domain/            # Pure business logic. No I/O, no framework imports.
    models/          # Entities & value objects (attrs; pydantic at boundaries — ADR-0006)
    agents/          # Pydantic AI agents, tools, capabilities (the assistant's core)
    ports/           # Protocols: interfaces the domain depends on (driven ports)
    services/        # Domain services / pure orchestration helpers
  application/        # Use cases. Orchestrates the domain through ports.
  adapter/
    input/           # Driving adapters. web/ (FastAPI) today; CLI, queue consumers,
                     #   jobs may follow as sibling segments
      web/
        models/      #   request/response DTOs (pydantic)
        routers/     #   APIRouter definitions + their DI providers
    output/          # Driven adapters: SQLAlchemy repositories, external API clients,
                     #   LLM provider/model wiring, and a mock for every external service
  infrastructure/     # Composition root: the DI container (ADR-0009), settings, DB
                     #   session/transaction management, the FastAPI app factory (app.main:app)
```

### The dependency rule (enforced)

- `domain` imports **nothing** from `application`, `adapter`, or `infrastructure`,
  and **no** framework/I/O libraries (no FastAPI, SQLAlchemy, httpx, provider SDKs).
- `application` may import `domain` only.
- `adapter` may import `application` and `domain`.
- `infrastructure` may import anything — it is the only place that wires concretes
  to ports at startup.
- Dependencies always point inward. An outer layer is never imported by an inner one.

**One sanctioned exception (ADR-0009):** web routers may import the DI container
(`adapter -> infrastructure.container`) to reference providers with static
type-safety. It is whitelisted narrowly in import-linter
(`routers.* -> infrastructure.container`); no other `adapter -> infrastructure`
import is allowed, and `domain`/`application` purity is unaffected.

### Ports & adapters

- **Ports are Python `Protocol`s.** Driven ports (repositories, external services,
  LLM access) are declared in `domain/ports/` and implemented in `adapter/output/`.
- **Every external service has a mock adapter** alongside its real one, so the
  domain and use cases are testable without network or DB.
- **DTOs do not cross inward.** Request/response models (pydantic) live in
  `adapter/input/web/models/` and are mapped to/from domain models; the domain
  never imports a transport or persistence DTO.
- **SQLAlchemy is an adapter detail.** ORM models live in `adapter/output/`,
  mapped to/from domain models. The domain has no SQLAlchemy import.

### Load-bearing rule: where Pydantic AI lives

Pydantic AI is **business logic**, not infrastructure — the agent *is* the product.
Agents, tools, and capabilities live in **`domain/agents/`**, never in
`infrastructure/` or `adapter/`. What stays outside the domain is only the
*binding* of a concrete model/provider and credentials, which is injected via a
port at the composition root. Tools that reach external services depend on a
domain port, implemented by an output adapter.

(Pydantic AI structured outputs are pydantic models and may live in the domain;
this is the boundary-validation exception in ADR-0006, not a violation.)

## Consequences

**Positive**

- The core (agents + domain logic) is unit-testable with mocks, no network/DB.
- FastAPI, SQLAlchemy, and provider SDKs are swappable without touching business logic.
- Clear, predictable placement: a reviewer can reject a misplaced import on sight.

**Negative / trade-offs**

- Mapping between domain models and DTOs/ORM models is boilerplate the layering demands.
- More indirection than a flat FastAPI app — deliberate, accepted for testability and longevity.

## Enforcement

The dependency rule is **mechanically enforced**, not just documented:
[import-linter](https://github.com/seddonym/import-linter) contracts in
`backend/pyproject.toml` (`[tool.importlinter]`) encode the layered ordering and
forbid framework imports in the domain. They run via the `import-linter`
pre-commit hook (and can be run manually with `uv run lint-imports` from
`backend/`). A misplaced import fails the commit.

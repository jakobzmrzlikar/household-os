# ADR-0006 — attrs by default; pydantic at boundaries; never dataclasses

- **Status:** Accepted
- **Date:** 2026-06-24

## Context

The backend has three viable ways to define structured classes: stdlib
`dataclasses`, **attrs**, and **pydantic** (v2). Pydantic is central to the stack
(FastAPI DTOs, settings, Pydantic AI structured outputs), but pydantic validates
and coerces on every construction — overhead and semantics we do not want for
internal, already-trusted domain objects. We want one clear rule so the choice is
never re-litigated per class.

## Decision

1. **Never use stdlib `dataclasses`.** Prefer **attrs** in every case where a
   dataclass would otherwise be used.

2. **Use `attrs` by default** for internal classes: domain entities and value
   objects, domain services, and any class whose data is already trusted (not
   crossing a serialization/validation boundary).

3. **Use `pydantic` (v2) only at boundaries** — where untrusted or external data
   is parsed/validated/serialized:
   - FastAPI request/response DTOs (`adapter/inbound/`).
   - Application settings/config loaded from the environment.
   - **Pydantic AI structured outputs** — LLM output is untrusted text parsed into
     a validated structure, so these are pydantic and may live in `domain/agents/`
     (the boundary exception noted in ADR-0005).
   - Serialization to/from external APIs where validation adds value.

### attrs usage

- Import style: `from attrs import define, field`.
- `@define` for plain data classes.
- `@define(kw_only=True)` for service/node classes that benefit from keyword-only
  construction.

## Consequences

**Positive**

- Internal objects are cheap to construct (no per-instance validation) and have
  clear, explicit semantics.
- Pydantic's validation power is spent exactly where untrusted data enters the
  system, not scattered across the domain.
- A single rule removes per-class bikeshedding; misuse is reviewable on sight.

**Negative / trade-offs**

- Two modelling libraries in one codebase; contributors must learn the
  boundary rule (attrs inside, pydantic at the edges).
- Mapping between attrs domain models and pydantic DTOs is boilerplate — the same
  mapping the hexagonal boundary (ADR-0005) already requires.

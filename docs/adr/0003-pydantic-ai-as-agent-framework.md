# ADR-0003 — Pydantic AI as the agent framework

- **Status:** Accepted
- **Date:** 2026-06-24

## Context

sol is an AI travel assistant whose core is an LLM-driven agent: it reasons over
user requests, calls tools, and returns structured results. We need a framework
to structure agent definitions, tool calling, and — critically — typed,
validated inputs and outputs.

The backend is already FastAPI + Pydantic. Pydantic AI is built by the Pydantic
team and shares that model/validation foundation, so agent I/O, API schemas, and
domain models can all live in one type system rather than being bridged across
frameworks.

## Decision

Use **Pydantic AI** as the agent framework for sol.

- Define agents, their tools, and their dependencies with Pydantic AI.
- Use Pydantic models for structured agent outputs, reusing the same models that
  back the FastAPI layer where it makes sense.

## Consequences

**Positive**

- One consistent type/validation system across the agent, the API, and domain
  models (Pydantic everywhere).
- Structured, validated agent outputs reduce glue code and runtime surprises.
- Natural fit with the existing FastAPI + Pydantic backend.

**Negative / trade-offs**

- Ties the agent layer to Pydantic AI's maturity and release cadence.
- Model-provider and feature support is bounded by what Pydantic AI exposes; some
  cutting-edge capabilities may require working around the abstraction.

## Notes

Recorded now while the context is fresh; revisit if agent requirements outgrow
what Pydantic AI supports.

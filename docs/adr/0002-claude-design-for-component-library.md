# ADR-0002 — Claude Design + design-sync for the component library

- **Status:** Accepted
- **Date:** 2026-06-24

## Context

sol needs a frontend component library for its React UI. As a solo project, the
priority is to spend design/build time on product-specific surfaces rather than
hand-authoring and maintaining a generic component set from scratch.

We are already working within the Claude ecosystem (Claude Code, Pydantic AI),
and Claude Design provides a component library with a `design-sync` workflow to
keep the local component set aligned with the upstream design source.

## Decision

Use **Claude Design** as the component library, kept in sync via the
**design-sync** workflow.

- Adopt Claude Design components as the UI foundation for the React frontend.
- Use design-sync to pull/refresh components rather than manually copying or
  diverging from the source, so updates and fixes flow in with low effort.

## Consequences

**Positive**

- Less time spent building and maintaining baseline UI primitives.
- A consistent, coherent design language out of the box.
- design-sync gives a repeatable path to stay current with upstream.

**Negative / trade-offs**

- A dependency on the Claude Design source and the design-sync tooling.
- Customizations must be reconciled against sync updates; heavy local divergence
  would erode the benefit of staying synced.

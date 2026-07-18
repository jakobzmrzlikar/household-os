# ADR-0009 — dependency-injector for the composition root

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

The hexagonal architecture (ADR-0005) requires concrete adapters to be bound to
their ports at a single composition root in `infrastructure/`. The first cut of
the chat endpoint wired this with bare FastAPI `Depends`: each router declared a
placeholder provider that raised `NotImplementedError`, and the app factory
replaced it via `app.dependency_overrides[...]`.

That works for one dependency but has two problems that worsen as the graph
grows:

- The "real" provider lives nowhere — the default exists only to be overridden,
  so the wiring is split between the adapter (placeholder) and the composition
  root (override).
- Each new dependency repeats the placeholder-then-override dance, scattering
  bindings across modules instead of keeping them in one composition root.

## Decision

Adopt the [`dependency-injector`](https://python-dependency-injector.ets-labs.org/)
package and express the composition root as a declarative `Container` in
`app/infrastructure/container.py`.

- All adapter-to-port bindings live in the `Container` as providers
  (`providers.Singleton`, `providers.Factory`, ...). Swapping a binding repoints
  the whole graph from one place.
- Routers receive their use cases through `@inject` +
  `Depends(Provide[Container.chat_usecase])`, the library's canonical FastAPI
  form. The provider reference is a typed attribute access, so a wrong provider
  name is a basedpyright error and an import-time failure, not a runtime surprise.
- **Routers import the container.** This is the one sanctioned exception to the
  inward dependency rule (ADR-0005): a router (`adapter`) importing the container
  (`infrastructure`) is an upward edge. We allow it because (a) the use case
  already adopted a container, so the alternative — name-based `Provide["..."]` —
  is equally a service locator but *untyped*, and (b) static type-safety is a core
  project value (ADR-0007). The exception is scoped narrowly in import-linter:

  ```toml
  ignore_imports = ["app.adapter.input.web.routers.* -> app.infrastructure.container"]
  ```

  No other `adapter -> infrastructure` import is permitted. Domain and application
  purity — the load-bearing half of ADR-0005 — is untouched.
- The container is instantiated in the app factory (`infrastructure/app.py`),
  which auto-wires the configured router modules, and is held on `app.state` so
  it stays alive and tests can override providers.
- Tests override providers on the container instance
  (`container.chat_port.override(...)`) instead of patching call sites — the
  same seam the production graph uses.

## Consequences

**Positive**

- One composition root holds every binding; adding a dependency means adding a
  provider, not threading a new placeholder/override pair through two layers.
- Provider references are statically type-checked (attribute access on `Container`),
  consistent with the strict-typing stance of ADR-0007.
- Test doubles are injected by overriding a provider, consistent with the
  port-injection testing rule (ADR-0008, `tests.md`).
- The "wire concretes at startup" model of hexagonal architecture is expressed
  directly rather than emulated with override placeholders.

**Negative / trade-offs**

- A new runtime dependency with a C-extension core (one more thing to keep
  building on new Python versions; verified working on 3.14).
- ADR-0005 is no longer exception-free: there is now one whitelisted
  `adapter -> infrastructure` edge (router -> container). Reviewers must know it is
  the *only* sanctioned one, and the import-linter `ignore_imports` must stay
  scoped to `routers.* -> infrastructure.container`.
- Importing the container into a router is a mild service-locator smell (the
  composition-root principle says only the root knows the container). Mitigated by
  `@inject` resolving the marker at wiring time rather than at call time, and by
  the fact that the untyped name-based alternative is no less a locator.
- Some magic: wiring patches the router modules at container construction, which
  is less obvious than an explicit `Depends`.

## Notes

Recorded when the dependency graph was still just chat, so the convention is set
cheaply before it spreads. The container-import exception and the canonical
`Provide[Container.x]` form are codified in `.claude/rules/adapters.md`.

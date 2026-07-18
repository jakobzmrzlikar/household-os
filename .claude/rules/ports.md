---
paths: "backend/**/ports/**/*.py"
---

# Port (Protocol) Definitions

Ports define the contracts between layers in the hexagonal architecture (ADR-0005).
They are Python `Protocol`s, depended on by inner layers and implemented by adapters.

- `app/domain/ports/` — **driven ports**: contracts the domain depends on, implemented
  by output adapters (repositories, external service clients, LLM access).
- `app/application/ports/` — **use-case (driving) ports**, if/when introduced: the
  input contracts a use case exposes to inbound adapters.

A port file imports only stdlib, typing, attrs, and domain types — never a framework
or I/O library (enforced by import-linter, ADR-0005).

## File Structure

Organize port files in this order. This **overrides** the general module-level table
in [code-ordering.md](code-ordering.md): Protocols are promoted above Enums because the
Protocol is the primary contract the file exists to define.

1. **Imports** — stdlib, third-party, project modules
2. **Constants** — validation limits, default values
3. **Protocols** — the port interface definitions
4. **Enums** — any enumeration types used by the port
5. **Data classes** — request/response objects using attrs `@define`
6. **Private functions** — validators and helpers (e.g. `_validate_max_options`)

## Data Classes

Request/response objects crossing a port are internal (already-trusted) data, so they
use attrs `@define`, not pydantic (ADR-0006):

```python
from attrs import define, field


@define
class TripSearchRequest:
    """Criteria for a trip search.

    :param destination: Target destination name.
    :param max_options: Upper bound on the number of options returned.
    """

    destination: str
    max_options: int = field(default=10)
```

## Protocol Definitions

Always use the `@runtime_checkable` decorator:

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class TripSearchPort(Protocol):
    """Port for searching bookable trip options from a travel provider."""

    async def search(self, request: TripSearchRequest) -> TripSearchResponse:
        """Search for trip options matching the request.

        :param request: The destination and constraints to search with.
        :return: The matching trip options.
        :raises TripSearchError: When the upstream provider is unavailable.
        """
        ...
```

## Key Conventions

1. **Method bodies end with `...`** — not `pass`, not `raise NotImplementedError`.
2. **All I/O methods are async** — use `async def` for any operation that may involve I/O.
3. **Full reST docstrings** — `:param:`, `:return:`, `:raises:` (omit `:type:`/`:rtype:`;
   type hints in the signature suffice). See [documentation.md](documentation.md).
4. **Type hints required** — every parameter and return type is annotated (basedpyright
   runs strict, ADR-0007).
5. **Focused interfaces** — one responsibility per port (Interface Segregation). Prefer
   several small ports over one broad one.

## Naming Conventions

- Port files: `{concept}.py` (e.g. `trip_search.py`, `itinerary_repository.py`).
- Protocol names: `{Concept}Port` (e.g. `TripSearchPort`, `ItineraryRepositoryPort`);
  an action-oriented name (`SearchTripsPort`) is fine for a single-method port.
- Request objects: `{Concept}Request`.
- Response objects: `{Concept}Response` (or a domain type when the response is one).

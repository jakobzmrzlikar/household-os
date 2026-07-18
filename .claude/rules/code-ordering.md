---
paths: "backend/**/*.py"
---

# Code Ordering Conventions (Newspaper Principle)

Organize code so readers encounter the most important, high-level abstractions first
and private implementation details last -- like a newspaper article where the
headline comes before the body.

## Module-Level Ordering

| Order | Element |
|-------|---------|
| 1 | Module docstring |
| 2 | Imports (stdlib, third-party, project) |
| 3 | Constants and type variables (`logger`, then `TypeVar`/`TypeAlias`/`ParamSpec`, then `SCREAMING_SNAKE_CASE` constants) |
| 4 | Enums |
| 5 | Base / abstract classes (includes `Protocol` definitions) |
| 6 | Concrete classes (dependency order -- if class A uses class B, define B first) |
| 7 | Public standalone functions |
| 8 | Private standalone functions |

`__all__` declarations (in `__init__.py` files) go immediately after imports, before
constants. Items within `__all__` should be sorted alphabetically.

- Factory functions (`build_*`, `create_*`) belong after the class they construct,
  within the public standalone functions section.
- Composition/builder functions that assemble multiple classes (e.g. wiring an
  adapter into a use case) belong in the public standalone functions section, after
  all the classes they compose.

## Class Member Ordering

| Order | Member |
|-------|---------|
| 1 | Class constants |
| 2 | Fields (attrs `@define` / pydantic model fields) |
| 2a | Attrs validators (`@field.validator`) |
| 3 | `__init__` / `__attrs_post_init__` / construction classmethods (`from_*`, `create`) |
| 4 | `__call__` |
| 5 | Abstract properties and methods |
| 6 | Public properties |
| 7 | Private properties |
| 8 | Public methods |
| 9 | Private methods |
| 10 | Dunder methods (`__str__`, `__repr__`, `__eq__`) |

Attrs `@field.validator` methods belong immediately after the field they validate
(row 2a). They are field configuration, not business logic, so readers expect them
alongside the fields they constrain.

Pydantic `model_config` goes immediately after fields (row 2), before `__init__`.
`@field_validator` and `@model_validator` come after `model_config`, in the public
methods section (row 8).

Construction classmethods (`from_*`, `create`) belong with row 3 -- they are
alternative constructors and readers expect all creation paths together. Other
`@classmethod` and `@staticmethod` belong with public methods (row 8, after instance
methods) -- they operate on the class or are standalone, so readers expect instance
behavior first.

Within Enum classes: member declarations first, then `@property` methods, then
`@classmethod` methods.

## Examples

### Entity class -- properties before methods, public before private

```python
# Correct
@define(frozen=True)
class Itinerary(Entity):
    """Immutable itinerary with ordered legs."""

    metadata: ItineraryMetadata                             # fields first
    legs: tuple[Leg, ...] = field(default=())

    @property
    def id(self) -> int:                                    # public properties
        return self.metadata.id

    @property
    def destination(self) -> str:
        return self.metadata.destination

    @property
    def leg_count(self) -> int:
        return len(self.legs)

    def with_leg(self, leg: Leg) -> Itinerary:              # public methods
        return evolve(self, legs=(*self.legs, leg))

    def llm_context(self) -> dict[str, Any]:
        return {"id": self.id, "destination": self.destination}


# Incorrect -- private helpers before public interface
@define(frozen=True)
class Itinerary(Entity):
    metadata: ItineraryMetadata
    legs: tuple[Leg, ...] = field(default=())

    def _validate_legs(self) -> None:                       # private first
        ...

    def llm_context(self) -> dict[str, Any]:                # methods before properties
        return {"id": self.id}

    @property
    def id(self) -> int:                                    # property buried below
        return self.metadata.id
```

### Callable service / use case -- `__call__` before private helpers

Use cases live in `application/`, are named `{Action}Usecase` (e.g. `PlanTripUsecase`,
`ChatUsecase` -- "Usecase" as one word) -- the suffix disambiguates them from
same-named ports/DTOs/entities -- and depend on **ports** (Protocols), injected as
fields (ADR-0005):

```python
@define(kw_only=True)
class PlanTripUsecase:
    """Use case: plan a trip from a destination query."""

    trip_search: TripSearchPort                             # fields (injected ports)
    ranker: OptionRanker

    async def __call__(self, destination: str) -> TripPlan:  # __call__ first
        options = await self._search(destination)
        return TripPlan(destination=destination, options=self._rank(options))

    async def _search(self, destination: str) -> list[TripOption]:  # private last
        return await self.trip_search.search(destination)

    def _rank(self, options: list[TripOption]) -> list[TripOption]:
        return self.ranker.rank(options)
```

## Test File Ordering

| Order | Element |
|-------|---------|
| 1 | Module docstring and imports |
| 2 | Module-level fixtures (shared across multiple test classes) |
| 3 | Mock / stub / helper classes (before the test class that uses them) |
| 4 | Test classes (class-level `@pytest.fixture` methods before `test_*` methods) |
| 5 | Standalone test functions |

## Notes

- **Private helpers called by a class at runtime**: A `_private_function` that is
  only called inside a method body does **not** need to be defined before the class.
  Python resolves the name at call time, not at class definition time. Always place
  these after the class per the module-level table (row 8 after row 6). The common
  mistake is placing them above the class "so the class can see them" -- that is only
  required when the function is referenced **during class body evaluation**.
- **Class-body evaluation**: Callables referenced while the class body executes --
  default field values, decorator arguments, or DI provider arguments -- must be
  defined **before** the class. Everything called only at runtime goes after.
- **Port modules** reverse rows 4 and 5: in a file whose purpose is to define a
  `Protocol` contract, the `Protocol` comes **before** any Enums, because it is the
  primary thing the module exists to declare. See [ports.md](ports.md) for the
  authoritative port-file ordering. The class-member ordering table still applies
  unchanged.
- **Do not add `from __future__ import annotations`.** When a Protocol references
  request/response types declared below it (the port ordering above), the future
  import is redundant on Python 3.14 (`backend/.python-version`): PEP 649/749 make
  annotations lazily evaluated, so the forward reference resolves at runtime and
  basedpyright accepts it. ruff's `F821`, however, statically flags a *bare*
  forward reference -- so **quote** just those annotations
  (`request: "ChatRequest"`) instead of reaching for the blanket future import.
- For **where** a class belongs (which module/layer), see the hexagonal layering in
  ADR-0005 and `CLAUDE.md`.
- When unsure where a member belongs, default to placing it **later** -- new public
  API is easy to move up, but buried private code is easy to overlook.
- Ruff does not enforce member ordering. This is a convention for code review and
  authoring; basedpyright will not flag it either.

---
paths: "backend/app/adapter/**"
---

# Adapter Conventions

Adapters connect the application/domain core to the outside world (ADR-0005).
They come in two directions and never import inward layers' implementation
details beyond the ports and use cases they target.

## Input vs. output

- `adapter/input/` — **driving (input) adapters**: things that call *into* the
  application (HTTP, CLI, queue consumers, scheduled jobs).
- `adapter/output/` — **driven (output) adapters**: things the application calls
  *out* to (SQLAlchemy repositories, external API clients, LLM wiring), each
  implementing a driven port from `domain/ports/`.

We use **input/output**, not inbound/outbound.

## Web (HTTP) input layout

HTTP adapters live under `adapter/input/web/`, split by concern so a transport
segment can sit beside future ones (CLI, queue) without entangling them:

```
adapter/input/web/
  models/      # pydantic request/response DTOs, one module per resource
  routers/     # APIRouter definitions + their DI providers, one module per resource
```

- **DTOs live in their own files**, never alongside a router or an adapter. The
  request/response models are boundary data contracts; the router is wiring. They
  change for different reasons and have different importers (tests asserting on
  the schema vs. the composition root wiring the router), so they stay separate.
- A resource named `chat` therefore has both `models/chat.py` (the
  `ApiChatRequest`/`ApiChatResponse` pydantic DTOs) and `routers/chat.py` (the
  router).

## Output adapters

- One module per concrete adapter (e.g. `output/agent_chat.py`).
- **Every external service has a mock adapter** alongside its real one (e.g.
  `output/mock_chat.py`) so use cases are testable without network or DB
  (see [tests.md](tests.md)).
- **Output adapters (mocks included) explicitly inherit the port they implement**
  (e.g. `class AgentChat(ChatPort):`). Ports are Protocols, so inheritance is not
  required for typing -- we do it because basedpyright then checks method
  signatures against the port *at the class definition* (drift is flagged where
  the adapter lives, not at some distant usage site), and because the
  relationship becomes greppable and IDE-navigable.
- Runtime caveat: Python does not enforce Protocol abstractness at runtime -- a
  subclass missing a port method inherits the `...` body and returns `None`.
  basedpyright catches this at instantiation sites (`Cannot instantiate abstract
  class`), which is why `tests/` is included in the type-check scope.

## Dependency injection (ADR-0009)

Wiring is a declarative `dependency-injector` container in
`infrastructure/container.py`. Adapters consume it as follows:

- **Routers import the container** and reference providers as typed attribute
  accesses -- the library's canonical FastAPI form. A wrong provider name is then
  a basedpyright/import-time error, not a runtime surprise:

  ```python
  from dependency_injector.wiring import Provide, inject
  from fastapi import APIRouter, Depends

  from app.infrastructure.container import Container

  router = APIRouter()


  @router.post("/chat")
  @inject
  async def post_chat(
      body: ApiChatRequest,
      chat_usecase: ChatUsecase = Depends(Provide[Container.chat_usecase]),
  ) -> ApiChatResponse:
      ...
  ```

- Name the injected parameter after its container provider (provider
  `chat_usecase` -> parameter `chat_usecase`), so a single grep surfaces the whole
  wiring chain: container binding -> `Provide` reference -> parameter -> call.

- This `router -> infrastructure.container` import is the **one sanctioned
  exception** to the inward dependency rule (ADR-0005/ADR-0009), whitelisted in
  import-linter as `routers.* -> infrastructure.container`. It applies *only* to
  the container module: no other `adapter -> infrastructure` import is allowed, and
  routers never import anything else from `infrastructure` (settings, sessions, the
  app factory).
- `@inject` is the innermost decorator (closest to the function); the route
  decorator wraps it.
- Use the canonical `param: T = Depends(...)` default-argument form. FastAPI's
  dependency markers are whitelisted in ruff's `flake8-bugbear.extend-immutable-calls`,
  so this does not trigger `B008` and needs no `Annotated` wrapper.
- Add new bindings to the `Container` and the resource module to its
  `wiring_config`; do not introduce `dependency_overrides` placeholders.

## Request samples (`.http`)

Every endpoint ships a matching `backend/requests/{resource}.http` with a sample
request, versioned alongside the code so examples can't drift from the API. Mirror
the existing `requests/health.http` style: a `### Title` line (the `###` delimiter
doubles as the request name in REST Client / the JetBrains HTTP client), the
method + `{{baseUrl}}` URL, and headers/body as needed.

Annotate the title with the expected response **only when it is a stable
contract** (e.g. `### Health check -> {"status": "ok"}`). For variable or generated
responses, hint at the **schema** instead (e.g. `### Chat -> { reply: string }`),
or omit the annotation -- never hardcode a response value that is expected to
change, since the `.http` file is not executed and nothing keeps it in sync.

## Naming

- Router/model/adapter modules: `{resource}.py` (e.g. `chat.py`).
- Pydantic DTOs: `Api{Resource}Request` / `Api{Resource}Response`, and `Api{Concept}`
  for nested models (e.g. `ApiChatTurn`). The transport prefix discriminates
  boundary DTOs from same-named domain/port models (`ChatRequest` the port object
  vs `ApiChatRequest` the HTTP schema): domain names stay clean, adapters carry
  the marker. A future non-HTTP input adapter uses its own transport prefix
  (e.g. `Cli...`).
- Output adapters: `{Concept}{Detail}` (e.g. `HardcodedChat`, `MockChat`,
  `HttpTripSearch`).

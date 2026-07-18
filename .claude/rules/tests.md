---
paths: "**/test_*.py"
---

# Test Conventions

Backend tests use **pytest** (+ pytest-asyncio, httpx) and live in `backend/tests/`.
See ADR-0008 for the testing strategy and `CLAUDE.md` for run commands.

## Test Naming

Use the pattern: `test_{unit}_should_{expected}_when_{condition}`

```python
# Good
def test_health_endpoint_should_return_ok_when_called(): ...
def test_trip_repository_should_return_trip_when_id_exists(): ...
def test_search_agent_should_raise_error_when_destination_missing(): ...

# Bad
def test_trip():          # too vague
def test_it_works():      # not descriptive
def test_repo_test():     # redundant "test"
```

## Async Tests

`asyncio_mode = "auto"` is set, so **async tests need no marker** — do **not** add
`@pytest.mark.asyncio`. Just write `async def`:

```python
async def test_search_agent_should_return_options_when_query_valid(search_agent):
    result = await search_agent.run("weekend in Lisbon")
    assert result.output.options
```

## Test Markers

`--strict-markers` is enabled: **every marker must be registered** in
`backend/pyproject.toml` under `[tool.pytest.ini_options].markers`. Using an
unregistered marker is an error, not a skip. To add a new category (e.g. a
`postgres` marker when a database is introduced), register it there **first**.

Currently registered:

| Marker | Meaning |
|--------|---------|
| `@pytest.mark.integration` | Requires external services (DB, network, LLM APIs). Excluded with `-m "not integration"`. |
| `@pytest.mark.slow` | Long-running tests. |

## Prefer Port Injection Over Patching

This codebase is hexagonal (ADR-0005): the domain and application layers depend on
**ports** (Protocols), and every external service has a **mock adapter** in
`app/adapter/output/`. Test by **injecting the mock adapter**, not by patching
HTTP clients or SDKs. Patch the network only when testing an output adapter itself.

```python
# Preferred: inject a mock implementation of the port
async def test_plan_trip_should_use_results_when_search_succeeds():
    usecase = PlanTripUsecase(trip_search=MockTripSearch(results=[lisbon_option]))

    plan = await usecase.execute(destination="Lisbon")

    assert plan.options == [lisbon_option]
```

## Fixtures

### Mock Adapter Fixture (unit)

```python
@pytest.fixture
def trip_search() -> TripSearchPort:
    """Mock output adapter with canned results for unit tests."""
    return MockTripSearch(results=[lisbon_option])
```

### Real Adapter Fixture (integration)

```python
@pytest.fixture
def real_trip_search() -> TripSearchPort:
    """Real adapter for integration tests; skips when config is absent.

    Requires env vars:
    - SOL__TRIP_SEARCH__BASE_URL
    - SOL__TRIP_SEARCH__API_KEY
    """
    base_url = os.getenv("SOL__TRIP_SEARCH__BASE_URL")
    api_key = os.getenv("SOL__TRIP_SEARCH__API_KEY")
    if not base_url or not api_key:
        pytest.skip("Missing SOL__TRIP_SEARCH__* env vars")
    return HttpTripSearch(base_url=base_url, api_key=api_key)
```

## Testing FastAPI Endpoints

Use `TestClient` for synchronous endpoint tests:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint_should_return_ok_when_called():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

For async endpoint tests, use `httpx.AsyncClient` with `ASGITransport`:

```python
import httpx
from app.main import app

async def test_trips_endpoint_should_return_201_when_payload_valid():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/trips", json={"destination": "Lisbon"})
    assert response.status_code == 201
```

## Test Structure

Follow Arrange-Act-Assert:

```python
async def test_plan_trip_should_return_plan_when_request_valid(trip_search):
    # Arrange
    usecase = PlanTripUsecase(trip_search=trip_search)

    # Act
    plan = await usecase.execute(destination="Lisbon")

    # Assert
    assert plan.destination == "Lisbon"
    assert plan.options
```

## Mocking

Use `AsyncMock` for async methods/ports; patch external calls only at the adapter boundary:

```python
from unittest.mock import AsyncMock, patch

# Async port double
mock_search = AsyncMock(spec=TripSearchPort)
mock_search.search.return_value = [lisbon_option]

# Patching httpx inside an output adapter under test
@patch("app.adapter.output.http_trip_search.httpx.AsyncClient.get")
async def test_http_trip_search_should_parse_options_when_api_returns_200(mock_get):
    mock_get.return_value = httpx.Response(200, json={"options": [...]})
    ...
```

## File Organization

Tests mirror the `app/` package structure:

```
backend/
├── app/
│   ├── adapter/output/http_trip_search.py
│   └── domain/agents/search_agent.py
└── tests/
    ├── adapter/output/test_http_trip_search.py
    └── domain/agents/test_search_agent.py
```

## Running Tests

See root `CLAUDE.md` for test execution commands.

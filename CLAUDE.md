# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**household-os** is a shared operating system for a household: flatmates or couples capture receipts (camera) and quick notes (voice); the backend extracts structured data, maintains shared pantry + expense state, and drafts actions (shopping orders, expense splits, restock reminders) that members approve with one tap. Built at a mobile-app hackathon.

It is a **monorepo**:

- `frontend/mobile/` — Expo (React Native) app; capture screens, approval queue, household feed.
- `backend/` — FastAPI + Pydantic AI service (the Python project; `pyproject.toml` + `uv.lock` live here).
- `docs/adr/` — Architecture Decision Records (the engineering "why").

## Domain model and API rules

Core entities (SQLAlchemy in `adapter/output/`, attrs domain models in `domain/models/`): **Household** (the tenant; all state belongs to exactly one), **Member** (a user in a household; demo auth is a simple member picker, no real auth), **PantryItem** (name, quantity, unit, restock threshold), **ExpenseEntry** (amount, payer, split between members), **Capture** (uploaded photo or voice note + its extraction result), **PendingCommand** (an agent-proposed action awaiting approval), **FeedItem** (what the home screen shows).

Non-negotiable API rules:

- **All writes are typed commands (verbs).** `log_receipt`, `adjust_pantry_item`, `propose_shopping_order`, `record_expense`, `approve_command`, `reject_command`. No generic CRUD/update/delete endpoints, ever. Each verb validates its invariants in code (e.g. quantities non-negative, splits sum to the expense amount, no cross-household references).
- **Agent output is always staged, never executed.** Agents (extraction, drafting) produce `PendingCommand` rows — fully materialized, inert. Only `approve_command`, invoked by a member, executes the underlying verb. Approval revalidates against current state; a stale command fails closed and returns why.
- **Every `PendingCommand` carries provenance**: which agent produced it, from which Capture, for which member to approve.
- **The model is swappable.** All LLM calls go through ports; concrete provider binding lives in the composition root only.
- **No chat endpoint.** The app has no free-text chat surface; inputs are captures, taps, and form fields.

## Backend

The Python backend lives in `backend/`. **Run all backend commands from `backend/`.**

### Environment setup
```bash
# One-time: install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create .venv/ and install all dependency groups
uv sync --all-groups

# Re-sync after pulling new commits or editing pyproject.toml
uv sync --all-groups
```

**Dependency management:**
- Single source of truth is `backend/pyproject.toml`. `backend/uv.lock` is the resolved lockfile and **must be committed**.
- `[project].dependencies` = runtime deps. `[dependency-groups].dev` = local + CI tooling.
- Add via `uv add <pkg>` (runtime) or `uv add --group dev <pkg>`. uv updates `pyproject.toml` and `uv.lock` automatically.
- This is an application, not a library: `[tool.uv] package = false`.

### Development
```bash
# Run FastAPI with auto-reload
uv run uvicorn app.main:app --reload   # GET /health -> {"status": "ok"}

# Lint and format
uv run ruff check --fix ./
uv run ruff format ./

# Enforce the hexagonal dependency rule (ADR-0005)
uv run lint-imports

# Strict static type checking (ADR-0007)
uv run basedpyright
# After deliberately accepting pre-existing errors:
uv run basedpyright --writebaseline
```

### Tests
pytest (async-ready via pytest-asyncio, `asyncio_mode = "auto"`). Tests live in `backend/tests/`. See ADR-0008.
```bash
uv run pytest                    # full suite
uv run pytest -m "not integration"   # skip tests needing external services
uv run pytest tests/test_health.py   # a single file
```
- Naming convention: `test_{unit}_should_{expected}_when_{condition}`.
- Mark slow/external tests `@pytest.mark.integration`.
- Tests run in **CI on every push/PR**, but are deliberately **not** a pre-commit hook (commits stay fast). Run `uv run pytest` before pushing.

### Database migrations (Alembic)
SQLAlchemy 2.0 models + Alembic are part of the stack. Alembic is **not initialized yet**
(`uv run alembic init alembic`). Once it is, the workflow is:
```bash
# Generate a migration after modifying SQLAlchemy models
uv run alembic revision --autogenerate -m "Description of change"

# Apply all pending migrations
uv run alembic upgrade head

# Rollback last migration
uv run alembic downgrade -1

# Current version / preview SQL
uv run alembic current
uv run alembic upgrade head --sql
```

### Linting and formatting
The project uses **Ruff** for both, configured in `backend/pyproject.toml`.

**Always run `ruff check` and `ruff format` on the entire backend (`./`), not just the
files you changed** — test files included. Never scope lint/format to individual files.

## Backend architecture — Hexagonal (ports & adapters), strictly enforced

See **ADR-0005**. `backend/app/` is layered with dependencies pointing **inward only**:

```
backend/app/
  domain/        # Pure business logic. No framework/I/O imports.
    models/      #   entities & value objects (attrs; pydantic only at boundaries)
    agents/      #   Pydantic AI agents, tools, capabilities — the assistant core
    ports/       #   Protocols the domain depends on (driven ports)
    services/    #   domain services / pure orchestration
  application/    # Use cases. Orchestrates the domain through ports.
  adapter/
    input/       #   driving adapters; web/ = FastAPI routers + pydantic DTOs (CLI/queue later)
      web/
        models/  #     request/response DTOs (pydantic)
        routers/ #     APIRouter definitions + their DI providers
    output/      #   SQLAlchemy repos, external clients, LLM wiring, + a mock per service
  infrastructure/ # Composition root: DI container (ADR-0009), settings, DB sessions, app factory
```

**The dependency rule (do not violate):**
- `domain` imports nothing from outer layers and **no** framework/I/O libs (no FastAPI, SQLAlchemy, httpx, provider SDKs).
- `application` → `domain` only. `adapter` → `application` + `domain`. `infrastructure` → anything (it wires concretes to ports at startup).
- Ports are Python `Protocol`s in `domain/ports/`, implemented in `adapter/output/`. Every external service has a **mock adapter** for testing.
- **Pydantic AI lives in `domain/agents/`** — the agent is business logic, not infrastructure. Only the concrete model/provider binding is injected from the composition root.
- SQLAlchemy ORM models are an adapter detail (`adapter/output/`), mapped to/from domain models. The domain never imports SQLAlchemy.
- **DI is a declarative `dependency-injector` container** in `infrastructure/` (ADR-0009). Routers inject providers via the canonical `Provide[Container.x]` (typed). The router→container import is the *one* sanctioned exception to the inward rule, whitelisted narrowly in import-linter. See [adapters.md](.claude/rules/adapters.md).

> Before placing code, confirm the layer. A misplaced import (e.g. SQLAlchemy in `domain/`) is a defect, not a style nit.

## Stack

- **Python ≥ 3.14**, managed with **uv**. The exact interpreter is pinned to 3.14 in `backend/.python-version` (single source of truth for dev + CI); uv reads it automatically.
- **Pydantic v2** (≥ 2.13) for models/validation.
- **Pydantic AI v2** (≥ 2.0, stable since 2026-06-23) as the agent framework — see ADR-0003.
  Note the v2 harness-first model: a *capability* bundles an agent's tools, hooks,
  instructions, and model settings. The default install includes the OpenAI, Anthropic,
  and Google providers; others (bedrock, groq, mistral, …) are opt-in extras.
- **FastAPI** for the HTTP/API layer (`app.main:app`).
- **SQLAlchemy 2.0** + **Alembic** for persistence and migrations.
- **dependency-injector** for the composition root — a declarative container wiring adapters to ports (ADR-0009).

When building the agent or anything LLM-shaped, default to the latest Claude models.

## Conventions

### Commits
This repo enforces **Conventional Commits** via commitizen (pre-commit `commit-msg` hook) — see ADR-0004.
Format: `type(scope): subject`, e.g. `feat(backend): add propose_shopping_order command`. Applies to the whole monorepo.

### Pre-commit
Hooks are defined at the repo root in `.pre-commit-config.yaml` (uv-lock scoped to `backend/`,
ruff-check --fix, ruff-format, commitizen, import-linter for the hexagonal boundaries, and basedpyright for type checking). Install once per clone:
```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

### CI
`.github/workflows/ci.yml` is the enforced backstop on every push to `main` and every PR:
- **checks** job runs `pre-commit run --all-files` (uv-lock, ruff, import-linter, basedpyright) via `setup-uv`.
- **tests** job runs `uv run pytest` (tests run in CI, not on every commit — ADR-0008).
- **commit-messages** job (PRs only) runs `cz check` over the PR commit range for Conventional Commits.

CI re-runs the same hooks, so a `--no-verify` or un-installed local hook cannot slip past.

### Data classes — attrs by default, pydantic at boundaries (ADR-0006)
- **Never use stdlib `dataclasses`.** Prefer **attrs** everywhere a dataclass would be used.
- **attrs by default** for internal/trusted classes: domain entities, value objects, services. Import `from attrs import define, field`; `@define` for data, `@define(kw_only=True)` for service classes.
- **pydantic (v2) only at boundaries** where external/untrusted data is parsed: FastAPI DTOs, settings from env, Pydantic AI structured outputs, external-API serialization.

### Code style
- Import order: (1) stdlib, (2) third-party, (3) project modules — separated by blank lines, all at top of file (never inline). Ruff's isort enforces this.
- Type hints required for all function parameters and return values.
- Never use emojis in code, comments, or output.

## Project rules (`.claude/rules/`)

Detailed conventions live in `.claude/rules/`. **Before writing or modifying a
matching file, read the applicable rule.** Rules with a `paths` frontmatter apply to
matching files; rules without `paths` apply to all code.

| Rule | Applies to |
| --- | --- |
| [documentation.md](.claude/rules/documentation.md) | all code — docstrings (reST/Sphinx) & inline comments |
| [code-ordering.md](.claude/rules/code-ordering.md) | `backend/**/*.py` — newspaper-principle module & class member ordering |
| [ports.md](.claude/rules/ports.md) | `backend/**/ports/**/*.py` — Protocol-first ordering, attrs request/response, naming |
| [adapters.md](.claude/rules/adapters.md) | `backend/app/adapter/**` — input/output split, web/models+routers layout, DI provider wiring, `.http` files |
| [tests.md](.claude/rules/tests.md) | `**/test_*.py` — pytest naming, markers, fixtures, port injection |

## Architecture Decision Records

Significant engineering decisions live in `docs/adr/` (see `docs/adr/README.md` for the index).
Add a new ADR rather than editing an accepted one; supersede when a decision changes.

Current ADRs:
- **ADR-0001** — Monorepo for frontend + backend.
- **ADR-0002** — Claude Design + design-sync for the component library.
- **ADR-0003** — Pydantic AI as the agent framework.
- **ADR-0004** — Python tooling: uv, ruff, commitizen + pre-commit.
- **ADR-0005** — Hexagonal architecture (ports & adapters) for the backend — *load-bearing for code placement*.
- **ADR-0006** — attrs by default; pydantic at boundaries; never dataclasses.
- **ADR-0007** — basedpyright for strict backend type checking.
- **ADR-0008** — Testing with pytest; run in CI, not on every commit.

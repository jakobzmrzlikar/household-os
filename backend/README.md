# household-os backend

FastAPI + Pydantic AI backend for household-os.

## Stack

- **uv** — dependency & environment management ([`pyproject.toml`](pyproject.toml), `uv.lock`)
- **ruff** — lint + format
- **commitizen** — Conventional Commits / version bumping
- **FastAPI + Pydantic AI** — API and agent layer

## Setup

```bash
cd backend
uv sync            # create .venv and install deps from uv.lock
```

## Run

```bash
uv run uvicorn app.main:app --reload
```

`GET /health` returns `{"status": "ok"}`.

## Quality

```bash
uv run ruff check --fix .
uv run ruff format .
```

Linting/formatting also run automatically via the repo-root pre-commit hooks
(see `../.pre-commit-config.yaml`).

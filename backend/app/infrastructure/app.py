"""Composition root: build the FastAPI app and wire the DI container."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapter.input.web.routers import (
    capture,
    extraction,
    health,
    pending_command,
)
from app.infrastructure.container import Container
from app.infrastructure.database import create_schema


def create_app() -> FastAPI:
    """Build the FastAPI application and wire its dependency container.

    Instantiating the container wires the configured router modules so their
    ``Provide`` markers resolve to concrete adapters (ADR-0009). The container is
    held on ``app.state`` so it stays alive and tests can override its providers.

    :return: The fully wired FastAPI application.
    """
    container = Container()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        # Schema bootstrap in lieu of Alembic migrations (not initialized yet).
        await create_schema(container.engine())
        yield

    app = FastAPI(title="household-os", version="0.1.0", lifespan=lifespan)
    app.state.container = container
    app.include_router(health.router)
    app.include_router(capture.router)
    app.include_router(extraction.router)
    app.include_router(pending_command.router)

    return app

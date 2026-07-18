"""Composition root: build the FastAPI app and wire the DI container."""

from fastapi import FastAPI

from app.adapter.input.web.routers import health
from app.infrastructure.container import Container


def create_app() -> FastAPI:
    """Build the FastAPI application and wire its dependency container.

    Instantiating the container wires the configured router modules so their
    ``Provide`` markers resolve to concrete adapters (ADR-0009). The container is
    held on ``app.state`` so it stays alive and tests can override its providers.

    :return: The fully wired FastAPI application.
    """
    container = Container()

    app = FastAPI(title="household-os", version="0.1.0")
    app.state.container = container
    app.include_router(health.router)

    return app

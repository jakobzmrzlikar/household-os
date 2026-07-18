"""ASGI entrypoint: the FastAPI app assembled by the composition root."""

from app.infrastructure.app import create_app

app = create_app()

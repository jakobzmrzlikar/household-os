"""Driven port for persisting Capture entities."""

from typing import Protocol, runtime_checkable

from app.domain.models.capture import Capture


@runtime_checkable
class CaptureRepositoryPort(Protocol):
    """Port for persisting captures."""

    async def add(self, capture: Capture) -> None:
        """Persist a new capture.

        :param capture: The capture to persist.
        """
        ...

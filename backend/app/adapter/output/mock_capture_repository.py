"""In-memory mock of the capture repository port for tests."""

from attrs import define, field

from app.domain.models.capture import Capture
from app.domain.ports.capture_repository import CaptureRepositoryPort


@define
class MockCaptureRepository(CaptureRepositoryPort):
    """Capture repository keeping captures in an in-memory list."""

    captures: list[Capture] = field(factory=list)

    async def add(self, capture: Capture) -> None:
        """Record the capture in memory.

        :param capture: The capture to record.
        """
        self.captures.append(capture)

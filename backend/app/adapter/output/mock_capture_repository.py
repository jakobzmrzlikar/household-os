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

    async def get(self, capture_id: str) -> Capture | None:
        """Look up a recorded capture by id.

        :param capture_id: Identifier of the capture to fetch.
        :return: The capture, or ``None`` when none was recorded with that id.
        """
        return next(
            (capture for capture in self.captures if capture.id == capture_id), None
        )

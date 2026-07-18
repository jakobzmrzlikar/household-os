"""SQLAlchemy implementation of the capture repository port."""

from attrs import define
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapter.output.orm import CaptureRecord
from app.domain.models.capture import Capture
from app.domain.ports.capture_repository import CaptureRepositoryPort


@define(kw_only=True)
class SqlAlchemyCaptureRepository(CaptureRepositoryPort):
    """Capture repository backed by a relational database."""

    session_factory: async_sessionmaker[AsyncSession]

    async def add(self, capture: Capture) -> None:
        """Persist a new capture row.

        :param capture: The capture to persist.
        """
        async with self.session_factory() as session, session.begin():
            session.add(_to_record(capture))


def _to_record(capture: Capture) -> CaptureRecord:
    """Map a domain capture to its relational record.

    :param capture: The domain capture to map.
    :return: The ORM record ready to be added to a session.
    """
    return CaptureRecord(
        id=capture.id,
        household_id=capture.household_id,
        member_id=capture.member_id,
        kind=capture.kind.value,
        media_path=capture.media_path,
        created_at=capture.created_at,
    )

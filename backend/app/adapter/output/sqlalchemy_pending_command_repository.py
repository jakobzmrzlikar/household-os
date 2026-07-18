"""SQLAlchemy implementation of the pending command repository port."""

import json

from attrs import define
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapter.output.orm import PendingCommandRecord
from app.domain.models.pending_command import (
    CommandVerb,
    PendingCommand,
    PendingCommandStatus,
    Provenance,
)
from app.domain.ports.pending_command_repository import PendingCommandRepositoryPort


@define(kw_only=True)
class SqlAlchemyPendingCommandRepository(PendingCommandRepositoryPort):
    """Pending command repository backed by a relational database."""

    session_factory: async_sessionmaker[AsyncSession]

    async def add(self, command: PendingCommand) -> None:
        """Persist a new pending command row.

        :param command: The pending command to persist.
        """
        async with self.session_factory() as session, session.begin():
            session.add(_to_record(command))

    async def list_pending(self, household_id: str) -> list[PendingCommand]:
        """Fetch a household's rows with status ``pending``.

        :param household_id: Household whose pending commands to list.
        :return: The pending commands, oldest first.
        """
        statement = (
            select(PendingCommandRecord)
            .where(
                PendingCommandRecord.household_id == household_id,
                PendingCommandRecord.status == PendingCommandStatus.PENDING.value,
            )
            .order_by(PendingCommandRecord.created_at)
        )
        async with self.session_factory() as session:
            records = (await session.scalars(statement)).all()
        return [_to_domain(record) for record in records]


def _to_record(command: PendingCommand) -> PendingCommandRecord:
    """Map a domain pending command to its relational record.

    :param command: The domain pending command to map.
    :return: The ORM record ready to be added to a session.
    """
    return PendingCommandRecord(
        id=command.id,
        household_id=command.household_id,
        capture_id=command.capture_id,
        verb=command.verb.value,
        payload=json.dumps(command.payload),
        agent_name=command.provenance.agent_name,
        model_id=command.provenance.model_id,
        status=command.status.value,
        created_at=command.created_at,
    )


def _to_domain(record: PendingCommandRecord) -> PendingCommand:
    """Map a relational record back to its domain pending command.

    :param record: The ORM record to map.
    :return: The domain pending command.
    """
    payload: dict[str, object] = json.loads(record.payload)
    return PendingCommand(
        id=record.id,
        household_id=record.household_id,
        capture_id=record.capture_id,
        verb=CommandVerb(record.verb),
        payload=payload,
        provenance=Provenance(agent_name=record.agent_name, model_id=record.model_id),
        status=PendingCommandStatus(record.status),
        created_at=record.created_at,
    )

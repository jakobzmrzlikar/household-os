"""SQLAlchemy implementation of the pending command repository port."""

import json

from attrs import define
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    """Pending command repository bound to one open session.

    Constructed by the unit of work and never commits: the owning unit of
    work controls the transaction boundary, so writes from all repositories
    sharing the session land atomically.
    """

    session: AsyncSession

    async def add(self, command: PendingCommand) -> None:
        """Stage a new pending command row in the session.

        :param command: The pending command to persist.
        """
        self.session.add(_to_record(command))

    async def get(self, command_id: str) -> PendingCommand | None:
        """Fetch a command row by primary key, regardless of status.

        :param command_id: Identifier of the command to fetch.
        :return: The command, or ``None`` when no row has that id.
        """
        record = await self.session.get(PendingCommandRecord, command_id)
        return None if record is None else _to_domain(record)

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
        records = (await self.session.scalars(statement)).all()
        return [_to_domain(record) for record in records]

    async def update(self, command: PendingCommand) -> None:
        """Overwrite the mutable fields of an existing command row.

        :param command: The command whose persisted state to overwrite.
        :raises LookupError: When no row has the command's id.
        """
        record = await self.session.get(PendingCommandRecord, command.id)
        if record is None:
            raise LookupError(f"No pending command with id {command.id!r}")
        record.status = command.status.value
        record.decided_by = command.decided_by
        record.decided_at = command.decided_at


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
        decided_by=command.decided_by,
        decided_at=command.decided_at,
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
        decided_by=record.decided_by,
        decided_at=record.decided_at,
    )

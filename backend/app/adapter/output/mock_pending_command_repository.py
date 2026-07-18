"""In-memory mock of the pending command repository port for tests."""

from attrs import define, field

from app.domain.models.pending_command import PendingCommand, PendingCommandStatus
from app.domain.ports.pending_command_repository import PendingCommandRepositoryPort


@define
class MockPendingCommandRepository(PendingCommandRepositoryPort):
    """Pending command repository keeping commands in an in-memory list."""

    commands: list[PendingCommand] = field(factory=list)

    async def add(self, command: PendingCommand) -> None:
        """Record the pending command in memory.

        :param command: The pending command to record.
        """
        self.commands.append(command)

    async def list_pending(self, household_id: str) -> list[PendingCommand]:
        """Filter recorded commands by household and pending status.

        :param household_id: Household whose pending commands to list.
        :return: The matching commands, in insertion order.
        """
        return [
            command
            for command in self.commands
            if command.household_id == household_id
            and command.status is PendingCommandStatus.PENDING
        ]

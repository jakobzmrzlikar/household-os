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

    async def get(self, command_id: str) -> PendingCommand | None:
        """Look up a recorded command by id, regardless of status.

        :param command_id: Identifier of the command to fetch.
        :return: The command, or ``None`` when none was recorded with that id.
        """
        return next(
            (command for command in self.commands if command.id == command_id), None
        )

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

    async def update(self, command: PendingCommand) -> None:
        """Replace the recorded command sharing the given command's id.

        :param command: The command whose recorded state to overwrite.
        :raises LookupError: When no command was recorded with the command's id.
        """
        for index, existing in enumerate(self.commands):
            if existing.id == command.id:
                self.commands[index] = command
                return
        raise LookupError(f"No pending command with id {command.id!r}")

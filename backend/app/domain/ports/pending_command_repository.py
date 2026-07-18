"""Driven port for persisting PendingCommand entities."""

from typing import Protocol, runtime_checkable

from app.domain.models.pending_command import PendingCommand


@runtime_checkable
class PendingCommandRepositoryPort(Protocol):
    """Port for persisting and querying staged pending commands."""

    async def add(self, command: PendingCommand) -> None:
        """Persist a new pending command.

        :param command: The pending command to persist.
        """
        ...

    async def get(self, command_id: str) -> PendingCommand | None:
        """Fetch a command by its identifier, regardless of status.

        :param command_id: Identifier of the command to fetch.
        :return: The command, or ``None`` when no command has that id.
        """
        ...

    async def list_pending(self, household_id: str) -> list[PendingCommand]:
        """Fetch a household's commands still awaiting approval.

        :param household_id: Household whose pending commands to list.
        :return: Commands with status ``pending``, oldest first.
        """
        ...

    async def update(self, command: PendingCommand) -> None:
        """Persist the current state of an already-staged command.

        :param command: The command whose persisted state to overwrite.
        :raises LookupError: When no persisted command has the command's id.
        """
        ...

"""Driven port for one atomic transaction across command-execution state."""

from types import TracebackType
from typing import Protocol, runtime_checkable

from app.domain.ports.expense_entry_repository import ExpenseEntryRepositoryPort
from app.domain.ports.pantry_item_repository import PantryItemRepositoryPort
from app.domain.ports.pending_command_repository import PendingCommandRepositoryPort


@runtime_checkable
class UnitOfWorkPort(Protocol):
    """Port for a single-transaction scope over the write-side repositories.

    Entering the context opens the transaction; exiting commits it, or rolls
    it back when an exception escapes the block. All writes through the
    exposed repositories take effect together or not at all — the guarantee
    approve_command relies on to execute a verb and mark its command approved
    atomically.
    """

    pending_commands: PendingCommandRepositoryPort
    pantry_items: PantryItemRepositoryPort
    expense_entries: ExpenseEntryRepositoryPort

    async def __aenter__(self) -> "UnitOfWorkPort":
        """Open the transactional scope.

        :return: This unit of work, its repositories bound to one transaction.
        """
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the scope, committing on success and rolling back on error.

        :param exc_type: Type of the exception that escaped the block, if any.
        :param exc: The escaping exception, if any.
        :param traceback: Traceback of the escaping exception, if any.
        """
        ...

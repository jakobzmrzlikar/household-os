"""In-memory mock of the unit of work port for tests."""

from types import TracebackType

from attrs import define, field

from app.adapter.output.mock_expense_entry_repository import (
    MockExpenseEntryRepository,
)
from app.adapter.output.mock_pantry_item_repository import MockPantryItemRepository
from app.adapter.output.mock_pending_command_repository import (
    MockPendingCommandRepository,
)
from app.domain.ports.expense_entry_repository import ExpenseEntryRepositoryPort
from app.domain.ports.pantry_item_repository import PantryItemRepositoryPort
from app.domain.ports.pending_command_repository import PendingCommandRepositoryPort
from app.domain.ports.unit_of_work import UnitOfWorkPort


@define(kw_only=True)
class MockUnitOfWork(UnitOfWorkPort):
    """Unit of work over the in-memory mocks, counting commits and rollbacks.

    In-memory writes are not transactional — a rollback does not undo them —
    so use cases must validate before writing. Tests assert transaction
    outcomes through the ``commits``/``rollbacks`` counters.
    """

    pending_commands: PendingCommandRepositoryPort = field(
        factory=MockPendingCommandRepository
    )
    pantry_items: PantryItemRepositoryPort = field(factory=MockPantryItemRepository)
    expense_entries: ExpenseEntryRepositoryPort = field(
        factory=MockExpenseEntryRepository
    )
    commits: int = 0
    rollbacks: int = 0

    async def __aenter__(self) -> "MockUnitOfWork":
        """Open the mock scope.

        :return: This unit of work, unchanged.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Count the outcome: a commit on success, a rollback on error.

        :param exc_type: Type of the exception that escaped the block, if any.
        :param exc: The escaping exception, if any.
        :param traceback: Traceback of the escaping exception, if any.
        """
        if exc_type is None:
            self.commits += 1
        else:
            self.rollbacks += 1

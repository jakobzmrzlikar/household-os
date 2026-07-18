"""SQLAlchemy implementation of the unit of work port."""

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapter.output.sqlalchemy_expense_entry_repository import (
    SqlAlchemyExpenseEntryRepository,
)
from app.adapter.output.sqlalchemy_pantry_item_repository import (
    SqlAlchemyPantryItemRepository,
)
from app.adapter.output.sqlalchemy_pending_command_repository import (
    SqlAlchemyPendingCommandRepository,
)
from app.domain.ports.expense_entry_repository import ExpenseEntryRepositoryPort
from app.domain.ports.pantry_item_repository import PantryItemRepositoryPort
from app.domain.ports.pending_command_repository import PendingCommandRepositoryPort
from app.domain.ports.unit_of_work import UnitOfWorkPort


class SqlAlchemyUnitOfWork(UnitOfWorkPort):
    """Unit of work sharing one session, and thus one transaction, across
    the pending command, pantry item, and expense entry repositories.

    Single-shot: create one per command execution. Not an attrs class because
    construction is wiring, not data — the instance creates its own session
    and binds one repository of each kind to it.
    """

    pending_commands: PendingCommandRepositoryPort
    pantry_items: PantryItemRepositoryPort
    expense_entries: ExpenseEntryRepositoryPort

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Create the shared session and bind the repositories to it.

        :param session_factory: Factory producing the session this unit owns.
        """
        self._session = session_factory()
        self.pending_commands = SqlAlchemyPendingCommandRepository(
            session=self._session
        )
        self.pantry_items = SqlAlchemyPantryItemRepository(session=self._session)
        self.expense_entries = SqlAlchemyExpenseEntryRepository(session=self._session)

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        """Open the transactional scope.

        :return: This unit of work; the transaction begins on first use.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Commit on success, roll back on error, and close the session.

        :param exc_type: Type of the exception that escaped the block, if any.
        :param exc: The escaping exception, if any.
        :param traceback: Traceback of the escaping exception, if any.
        """
        try:
            if exc_type is None:
                await self._session.commit()
            else:
                await self._session.rollback()
        finally:
            await self._session.close()

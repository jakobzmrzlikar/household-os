"""In-memory mock of the expense entry repository port for tests."""

from attrs import define, field

from app.domain.models.expense_entry import ExpenseEntry
from app.domain.ports.expense_entry_repository import ExpenseEntryRepositoryPort


@define
class MockExpenseEntryRepository(ExpenseEntryRepositoryPort):
    """Expense entry repository keeping entries in an in-memory list."""

    entries: list[ExpenseEntry] = field(factory=list)

    async def add(self, entry: ExpenseEntry) -> None:
        """Record the expense entry in memory.

        :param entry: The expense entry to record.
        """
        self.entries.append(entry)

"""Driven port for persisting ExpenseEntry entities."""

from typing import Protocol, runtime_checkable

from app.domain.models.expense_entry import ExpenseEntry


@runtime_checkable
class ExpenseEntryRepositoryPort(Protocol):
    """Port for persisting recorded expenses."""

    async def add(self, entry: ExpenseEntry) -> None:
        """Persist a new expense entry.

        :param entry: The expense entry to persist.
        """
        ...

"""SQLAlchemy implementation of the expense entry repository port."""

import json

from attrs import define
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapter.output.orm import ExpenseEntryRecord
from app.domain.models.expense_entry import ExpenseEntry
from app.domain.ports.expense_entry_repository import ExpenseEntryRepositoryPort


@define(kw_only=True)
class SqlAlchemyExpenseEntryRepository(ExpenseEntryRepositoryPort):
    """Expense entry repository bound to one open session.

    Constructed by the unit of work and never commits: the owning unit of
    work controls the transaction boundary.
    """

    session: AsyncSession

    async def add(self, entry: ExpenseEntry) -> None:
        """Stage a new expense entry row in the session.

        :param entry: The expense entry to persist.
        """
        self.session.add(_to_record(entry))


def _to_record(entry: ExpenseEntry) -> ExpenseEntryRecord:
    """Map a domain expense entry to its relational record.

    :param entry: The domain expense entry to map.
    :return: The ORM record ready to be added to a session.
    """
    return ExpenseEntryRecord(
        id=entry.id,
        household_id=entry.household_id,
        payer_member_id=entry.payer_member_id,
        merchant=entry.merchant,
        amount=entry.amount,
        currency=entry.currency,
        split=json.dumps(entry.split),
        created_at=entry.created_at,
    )

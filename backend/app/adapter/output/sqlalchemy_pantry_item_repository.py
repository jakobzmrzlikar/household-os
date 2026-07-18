"""SQLAlchemy implementation of the pantry item repository port."""

from attrs import define
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapter.output.orm import PantryItemRecord
from app.domain.models.pantry_item import PantryItem
from app.domain.ports.pantry_item_repository import PantryItemRepositoryPort


@define(kw_only=True)
class SqlAlchemyPantryItemRepository(PantryItemRepositoryPort):
    """Pantry item repository bound to one open session.

    Constructed by the unit of work and never commits: the owning unit of
    work controls the transaction boundary.
    """

    session: AsyncSession

    async def get(self, household_id: str, name: str) -> PantryItem | None:
        """Fetch a household's item row by its unique (household, name) key.

        :param household_id: Household the item belongs to.
        :param name: Name of the item within the household.
        :return: The item, or ``None`` when the household stocks no such item.
        """
        record = await self.session.scalar(_by_key(household_id, name))
        return None if record is None else _to_domain(record)

    async def upsert(self, item: PantryItem) -> None:
        """Insert the item row, or overwrite the row sharing its key.

        An existing row keeps its primary key; only the stocked state changes.

        :param item: The pantry item state to persist.
        """
        record = await self.session.scalar(_by_key(item.household_id, item.name))
        if record is None:
            self.session.add(_to_record(item))
            return
        record.quantity = item.quantity
        record.unit = item.unit
        record.restock_threshold = item.restock_threshold


def _by_key(household_id: str, name: str) -> Select[tuple[PantryItemRecord]]:
    """Build the select for a household's item by name.

    :param household_id: Household the item belongs to.
    :param name: Name of the item within the household.
    :return: The select statement for the matching record.
    """
    return select(PantryItemRecord).where(
        PantryItemRecord.household_id == household_id,
        PantryItemRecord.name == name,
    )


def _to_record(item: PantryItem) -> PantryItemRecord:
    """Map a domain pantry item to its relational record.

    :param item: The domain pantry item to map.
    :return: The ORM record ready to be added to a session.
    """
    return PantryItemRecord(
        id=item.id,
        household_id=item.household_id,
        name=item.name,
        quantity=item.quantity,
        unit=item.unit,
        restock_threshold=item.restock_threshold,
    )


def _to_domain(record: PantryItemRecord) -> PantryItem:
    """Map a relational record back to its domain pantry item.

    :param record: The ORM record to map.
    :return: The domain pantry item.
    """
    return PantryItem(
        id=record.id,
        household_id=record.household_id,
        name=record.name,
        quantity=record.quantity,
        unit=record.unit,
        restock_threshold=record.restock_threshold,
    )

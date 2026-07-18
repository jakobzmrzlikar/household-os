"""In-memory mock of the pantry item repository port for tests."""

from attrs import define, field

from app.domain.models.pantry_item import PantryItem
from app.domain.ports.pantry_item_repository import PantryItemRepositoryPort


@define
class MockPantryItemRepository(PantryItemRepositoryPort):
    """Pantry item repository keeping items in an in-memory mapping."""

    items: dict[tuple[str, str], PantryItem] = field(factory=dict)

    async def get(self, household_id: str, name: str) -> PantryItem | None:
        """Look up a recorded item by its (household, name) key.

        :param household_id: Household the item belongs to.
        :param name: Name of the item within the household.
        :return: The item, or ``None`` when none was recorded under that key.
        """
        return self.items.get((household_id, name))

    async def upsert(self, item: PantryItem) -> None:
        """Record the item under its (household, name) key, replacing any.

        :param item: The pantry item state to record.
        """
        self.items[(item.household_id, item.name)] = item

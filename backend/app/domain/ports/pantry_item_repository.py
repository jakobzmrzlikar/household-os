"""Driven port for persisting PantryItem entities."""

from typing import Protocol, runtime_checkable

from app.domain.models.pantry_item import PantryItem


@runtime_checkable
class PantryItemRepositoryPort(Protocol):
    """Port for persisting pantry items, keyed by household and item name."""

    async def get(self, household_id: str, name: str) -> PantryItem | None:
        """Fetch a household's pantry item by name.

        :param household_id: Household the item belongs to.
        :param name: Name of the item within the household.
        :return: The item, or ``None`` when the household stocks no such item.
        """
        ...

    async def upsert(self, item: PantryItem) -> None:
        """Insert the item, or overwrite the household's item of the same name.

        :param item: The pantry item state to persist.
        """
        ...

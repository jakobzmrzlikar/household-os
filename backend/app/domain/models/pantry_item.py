"""PantryItem entity: a household's stock of one pantry good."""

from attrs import Attribute, define, field


def _require_non_negative(
    instance: object, attribute: "Attribute[float]", value: float
) -> None:
    """Reject negative quantities and thresholds.

    :param instance: The instance under validation (unused).
    :param attribute: The attrs field being validated.
    :param value: The value assigned to the field.
    :raises ValueError: When the value is negative.
    """
    if value < 0:
        raise ValueError(f"{attribute.name} must be non-negative")


@define(frozen=True)
class PantryItem:
    """The household's current stock of one pantry good.

    Items are unique per household by ``name``; adjustments upsert on that key.
    The quantity can never drop below zero — an adjustment that would is
    rejected, not clamped.

    :param id: Unique identifier of the pantry item.
    :param household_id: Household the item belongs to.
    :param name: Item name, unique within the household.
    :param quantity: Current stock, in ``unit``; never negative.
    :param unit: Unit of measure (e.g. ``pcs``, ``kg``, ``l``).
    :param restock_threshold: Stock level at or below which a restock is due;
        never negative.
    """

    id: str
    household_id: str
    name: str
    quantity: float = field(validator=_require_non_negative)
    unit: str
    restock_threshold: float = field(default=0.0, validator=_require_non_negative)

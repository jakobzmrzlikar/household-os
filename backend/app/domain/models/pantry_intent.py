"""PantryIntent value object: one pantry change heard in a voice note."""

from attrs import Attribute, define, field


def _require_non_blank(
    instance: object, attribute: "Attribute[str]", value: str
) -> None:
    """Reject blank item names.

    :param instance: The instance under validation (unused).
    :param attribute: The attrs field being validated.
    :param value: The value assigned to the field.
    :raises ValueError: When the value is empty or whitespace-only.
    """
    if not value.strip():
        raise ValueError(f"{attribute.name} must not be blank")


@define(frozen=True)
class PantryIntent:
    """One pantry change a member voiced in an audio note.

    An intent must carry exactly one stock signal: either a signed quantity
    delta or the out-of-stock flag. An intent with neither says nothing; one
    with both is contradictory.

    :param name: Name of the pantry item the intent refers to.
    :param quantity_delta: Signed stock change (negative for consumption), or
        ``None`` when the note only declared the item out of stock.
    :param out_of_stock: Whether the note declared the item fully depleted.
    :param note: Free-text remark heard alongside the item, if any.
    """

    name: str = field(validator=_require_non_blank)
    quantity_delta: float | None = None
    out_of_stock: bool = False
    note: str | None = None

    def __attrs_post_init__(self) -> None:
        if (self.quantity_delta is None) == (not self.out_of_stock):
            raise ValueError(
                "an intent must carry exactly one of quantity_delta or out_of_stock"
            )

"""Receipt value objects extracted from a captured receipt photo."""

from attrs import Attribute, define, field


def _require_non_negative(
    instance: object, attribute: "Attribute[float]", value: float
) -> None:
    """Reject negative monetary amounts and quantities.

    :param instance: The instance under validation (unused).
    :param attribute: The attrs field being validated.
    :param value: The value assigned to the field.
    :raises ValueError: When the value is negative.
    """
    if value < 0:
        raise ValueError(f"{attribute.name} must be non-negative")


@define(frozen=True)
class ReceiptLineItem:
    """One purchased item on a receipt.

    :param name: Product name as printed on the receipt.
    :param quantity: Purchased quantity, in ``unit``.
    :param unit: Unit of measure (e.g. ``pcs``, ``kg``, ``l``).
    :param price: Total price of the line in the receipt currency.
    """

    name: str
    quantity: float = field(validator=_require_non_negative)
    unit: str
    price: float = field(validator=_require_non_negative)


@define(frozen=True)
class Receipt:
    """A structured shopping receipt extracted from a capture.

    :param merchant: Name of the merchant that issued the receipt.
    :param total: Grand total of the receipt.
    :param currency: ISO 4217 currency code of the amounts.
    :param line_items: The purchased items, in receipt order.
    """

    merchant: str
    total: float = field(validator=_require_non_negative)
    currency: str
    line_items: tuple[ReceiptLineItem, ...]

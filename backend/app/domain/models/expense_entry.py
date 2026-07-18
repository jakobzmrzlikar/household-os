"""ExpenseEntry entity: a paid expense split between household members."""

import math
from datetime import datetime

from attrs import Attribute, define, field

# Absorbs float representation error only (far below one cent); a genuinely
# wrong split differs from the amount by at least 0.01.
_SPLIT_SUM_TOLERANCE = 1e-6


def _require_positive(
    instance: object, attribute: "Attribute[float]", value: float
) -> None:
    """Reject non-positive monetary amounts.

    :param instance: The instance under validation (unused).
    :param attribute: The attrs field being validated.
    :param value: The value assigned to the field.
    :raises ValueError: When the value is zero or negative.
    """
    if value <= 0:
        raise ValueError(f"{attribute.name} must be positive")


@define(frozen=True)
class ExpenseEntry:
    """An expense one member paid, with each member's share of it.

    :param id: Unique identifier of the expense entry.
    :param household_id: Household the expense belongs to.
    :param payer_member_id: Member who paid the expense.
    :param merchant: Merchant the expense was paid to.
    :param amount: Total amount paid, in ``currency``; strictly positive.
    :param currency: ISO 4217 currency code of the amount.
    :param split: Share owed per member id; non-negative shares that sum
        exactly to ``amount``.
    :param created_at: When the expense was recorded (UTC).
    """

    id: str
    household_id: str
    payer_member_id: str
    merchant: str
    amount: float = field(validator=_require_positive)
    currency: str
    split: dict[str, float]
    created_at: datetime

    def __attrs_post_init__(self) -> None:
        """Enforce the split invariants against the amount.

        :raises ValueError: When a share is negative or the shares do not sum
            to the amount.
        """
        for member_id, share in self.split.items():
            if share < 0:
                raise ValueError(f"split share for {member_id!r} must be non-negative")
        total = sum(self.split.values())
        if not math.isclose(total, self.amount, abs_tol=_SPLIT_SUM_TOLERANCE):
            raise ValueError(
                f"split sums to {total}, expected the expense amount {self.amount}"
            )

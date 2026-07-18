"""Use case: list a household's staged commands awaiting approval."""

from collections.abc import Callable

from attrs import Attribute, define, field

from app.domain.models.pending_command import PendingCommand
from app.domain.ports.unit_of_work import UnitOfWorkPort


def _require_non_blank(
    instance: object, attribute: "Attribute[str]", value: str
) -> None:
    """Reject blank identifier values.

    :param instance: The instance under validation (unused).
    :param attribute: The attrs field being validated.
    :param value: The value assigned to the field.
    :raises ValueError: When the value is empty or whitespace-only.
    """
    if not value.strip():
        raise ValueError(f"{attribute.name} must not be blank")


@define
class ListPendingCommandsRequest:
    """The household whose pending commands to list.

    :param household_id: Household to list pending commands for.
    """

    household_id: str = field(validator=_require_non_blank)


@define(kw_only=True)
class ListPendingCommandsUsecase:
    """Use case: fetch the commands still awaiting a member's approval."""

    unit_of_work_factory: Callable[[], UnitOfWorkPort]

    async def __call__(
        self, request: ListPendingCommandsRequest
    ) -> list[PendingCommand]:
        """Execute the list_pending_commands query.

        :param request: The household to list pending commands for.
        :return: The household's pending commands, oldest first.
        """
        async with self.unit_of_work_factory() as unit_of_work:
            return await unit_of_work.pending_commands.list_pending(
                request.household_id
            )

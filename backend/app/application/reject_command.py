"""Use case: the reject_command command — discard a staged command unexecuted."""

from collections.abc import Callable
from datetime import UTC, datetime

from attrs import Attribute, define, field

from app.application.approve_command import CommandNotFoundError
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
class RejectCommandRequest:
    """The command to reject and the member rejecting it.

    :param command_id: Identifier of the staged command to reject.
    :param member_id: Member rejecting the command.
    """

    command_id: str = field(validator=_require_non_blank)
    member_id: str = field(validator=_require_non_blank)


@define(kw_only=True)
class RejectCommandUsecase:
    """Use case: mark a staged command rejected without executing anything.

    The proposed verb never runs; the command only stops being pending, with
    the rejecting member and time recorded.
    """

    unit_of_work_factory: Callable[[], UnitOfWorkPort]

    async def __call__(self, request: RejectCommandRequest) -> PendingCommand:
        """Execute the reject_command command.

        :param request: The command to reject and the rejecting member.
        :return: The command in its rejected state.
        :raises CommandNotFoundError: When no command has the requested id.
        :raises CommandNotPendingError: When the command was already decided.
        """
        async with self.unit_of_work_factory() as unit_of_work:
            command = await unit_of_work.pending_commands.get(request.command_id)
            if command is None:
                raise CommandNotFoundError(
                    f"No pending command with id {request.command_id!r}"
                )
            rejected = command.rejected(
                member_id=request.member_id, decided_at=datetime.now(UTC)
            )
            await unit_of_work.pending_commands.update(rejected)
            return rejected

"""Use case: the approve_command command — execute a staged command exactly once."""

from collections.abc import Callable
from datetime import UTC, datetime

from attrs import Attribute, define, field

from app.application.execute_verb import execute_verb
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


class CommandNotFoundError(LookupError):
    """Raised when no staged command has the requested id."""


@define
class ApproveCommandRequest:
    """The command to approve and the member approving it.

    :param command_id: Identifier of the staged command to approve.
    :param member_id: Member approving the command.
    """

    command_id: str = field(validator=_require_non_blank)
    member_id: str = field(validator=_require_non_blank)


@define(kw_only=True)
class ApproveCommandUsecase:
    """Use case: approve a staged command and execute its verb atomically.

    The verb is revalidated against current state and executed in the same
    transaction that marks the command approved: both happen or neither does.
    A stale, invalid, or already-decided command fails closed — the
    transaction rolls back, nothing executes, and the raised error carries
    the reason.
    """

    unit_of_work_factory: Callable[[], UnitOfWorkPort]

    async def __call__(self, request: ApproveCommandRequest) -> PendingCommand:
        """Execute the approve_command command.

        :param request: The command to approve and the approving member.
        :return: The command in its approved state.
        :raises CommandNotFoundError: When no command has the requested id.
        :raises CommandNotPendingError: When the command was already decided;
            the verb does not execute again (idempotency).
        :raises InvalidCommandError: When the payload fails revalidation
            against current state; nothing is executed.
        """
        async with self.unit_of_work_factory() as unit_of_work:
            command = await unit_of_work.pending_commands.get(request.command_id)
            if command is None:
                raise CommandNotFoundError(
                    f"No pending command with id {request.command_id!r}"
                )
            # Transition before executing: approved() fails closed on a
            # command that is no longer pending, so the verb can never run a
            # second time for the same command.
            approved = command.approved(
                member_id=request.member_id, decided_at=datetime.now(UTC)
            )
            await execute_verb(command, unit_of_work)
            await unit_of_work.pending_commands.update(approved)
            return approved

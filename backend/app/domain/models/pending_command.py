"""PendingCommand entity: an agent-proposed action awaiting member approval."""

from datetime import datetime
from enum import StrEnum
from typing import cast

from attrs import define, evolve


class CommandVerb(StrEnum):
    """Typed write command a pending command proposes to execute on approval."""

    RECORD_EXPENSE = "record_expense"
    ADJUST_PANTRY_ITEM = "adjust_pantry_item"


class PendingCommandStatus(StrEnum):
    """Approval state of a pending command."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CommandNotPendingError(ValueError):
    """Raised when deciding a command that is no longer pending (fail closed)."""


@define(frozen=True)
class Provenance:
    """Origin of an agent-proposed command.

    :param agent_name: Name of the agent that produced the proposal.
    :param model_id: Identifier of the model the agent ran on.
    :param transcript: Transcript of the voice note the proposal was derived
        from, shown in the approval UI; ``None`` for non-audio captures.
    """

    agent_name: str
    model_id: str
    transcript: str | None = None


@define(frozen=True)
class PendingCommand:
    """A fully materialized, inert command staged by an agent.

    Agents only ever produce these rows; nothing is executed until a member
    approves the command, at which point the underlying verb is revalidated
    against current state and run.

    :param id: Unique identifier of the pending command.
    :param household_id: Household the proposed action belongs to.
    :param capture_id: Capture the proposal was derived from.
    :param verb: The typed write command proposed for execution.
    :param payload: JSON-serializable arguments of the proposed verb.
    :param provenance: Which agent and model produced the proposal.
    :param status: Current approval state.
    :param created_at: When the proposal was staged (UTC).
    :param decided_by: Member who approved or rejected the command, if decided.
    :param decided_at: When the decision was made (UTC), if decided.
    """

    id: str
    household_id: str
    capture_id: str
    verb: CommandVerb
    payload: dict[str, object]
    provenance: Provenance
    status: PendingCommandStatus
    created_at: datetime
    decided_by: str | None = None
    decided_at: datetime | None = None

    def approved(self, member_id: str, decided_at: datetime) -> "PendingCommand":
        """Return this command approved by the given member.

        :param member_id: Member who approved the command.
        :param decided_at: When the decision was made (UTC).
        :return: A copy with status ``approved`` and the decision recorded.
        :raises CommandNotPendingError: When the command is no longer pending.
        """
        return self._decided(PendingCommandStatus.APPROVED, member_id, decided_at)

    def rejected(self, member_id: str, decided_at: datetime) -> "PendingCommand":
        """Return this command rejected by the given member.

        :param member_id: Member who rejected the command.
        :param decided_at: When the decision was made (UTC).
        :return: A copy with status ``rejected`` and the decision recorded.
        :raises CommandNotPendingError: When the command is no longer pending.
        """
        return self._decided(PendingCommandStatus.REJECTED, member_id, decided_at)

    def human_readable(self) -> str:
        """Summarize the proposed action for the approval UI.

        :return: A one-line, member-facing description of what approving
            this command would do.
        """
        if self.verb is CommandVerb.RECORD_EXPENSE:
            summary = (
                f"Record expense of {self.payload.get('amount')} "
                f"{self.payload.get('currency')} at {self.payload.get('merchant')}, "
                f"paid by {self.payload.get('payer_member_id')}"
            )
            split = self.payload.get("split")
            if isinstance(split, dict):
                members = len(cast("dict[str, object]", split))
                if members > 1:
                    summary += f", split between {members} members"
            return summary
        name = self.payload.get("name")
        if self.payload.get("out_of_stock"):
            return f"Mark {name} as out of stock in the pantry"
        quantity = self.payload.get("quantity")
        unit = self.payload.get("unit")
        # Voice-note adjustments carry no unit; drop it rather than print None.
        amount = f"{quantity} {unit}" if unit else f"{quantity}"
        if isinstance(quantity, int | float) and quantity < 0:
            amount = f"{-quantity} {unit}" if unit else f"{-quantity}"
            return f"Remove {amount} of {name} from the pantry"
        return f"Add {amount} of {name} to the pantry"

    def _decided(
        self, status: PendingCommandStatus, member_id: str, decided_at: datetime
    ) -> "PendingCommand":
        """Transition to a decided status, allowed only from pending.

        :param status: The decided status to transition to.
        :param member_id: Member who made the decision.
        :param decided_at: When the decision was made (UTC).
        :return: The decided copy of this command.
        :raises CommandNotPendingError: When the command is no longer pending.
        """
        if self.status is not PendingCommandStatus.PENDING:
            raise CommandNotPendingError(
                f"Command {self.id!r} is already {self.status.value}, not pending"
            )
        return evolve(self, status=status, decided_by=member_id, decided_at=decided_at)

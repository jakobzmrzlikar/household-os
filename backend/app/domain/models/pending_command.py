"""PendingCommand entity: an agent-proposed action awaiting member approval."""

from datetime import datetime
from enum import StrEnum

from attrs import define


class CommandVerb(StrEnum):
    """Typed write command a pending command proposes to execute on approval."""

    RECORD_EXPENSE = "record_expense"
    ADJUST_PANTRY_ITEM = "adjust_pantry_item"


class PendingCommandStatus(StrEnum):
    """Approval state of a pending command."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@define(frozen=True)
class Provenance:
    """Origin of an agent-proposed command.

    :param agent_name: Name of the agent that produced the proposal.
    :param model_id: Identifier of the model the agent ran on.
    """

    agent_name: str
    model_id: str


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
    """

    id: str
    household_id: str
    capture_id: str
    verb: CommandVerb
    payload: dict[str, object]
    provenance: Provenance
    status: PendingCommandStatus
    created_at: datetime

    def human_readable(self) -> str:
        """Summarize the proposed action for the approval UI.

        :return: A one-line, member-facing description of what approving
            this command would do.
        """
        if self.verb is CommandVerb.RECORD_EXPENSE:
            return (
                f"Record expense of {self.payload.get('amount')} "
                f"{self.payload.get('currency')} at {self.payload.get('merchant')}, "
                f"paid by {self.payload.get('payer_member_id')}, split equally"
            )
        return (
            f"Add {self.payload.get('quantity')} {self.payload.get('unit')} "
            f"of {self.payload.get('name')} to the pantry"
        )

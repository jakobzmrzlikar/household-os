"""Response DTOs for the list_pending_commands query endpoint."""

from datetime import datetime

from pydantic import BaseModel

from app.domain.models.pending_command import (
    CommandVerb,
    PendingCommand,
    PendingCommandStatus,
)


class ApiPendingCommand(BaseModel):
    """A staged command awaiting approval, as returned to the client."""

    id: str
    capture_id: str
    verb: CommandVerb
    payload: dict[str, object]
    agent_name: str
    model_id: str
    status: PendingCommandStatus
    created_at: datetime
    human_readable: str

    @classmethod
    def from_domain(cls, command: PendingCommand) -> "ApiPendingCommand":
        """Build the DTO for a domain pending command.

        :param command: The domain pending command to expose.
        :return: The DTO, with provenance flattened and the summary rendered.
        """
        return cls(
            id=command.id,
            capture_id=command.capture_id,
            verb=command.verb,
            payload=command.payload,
            agent_name=command.provenance.agent_name,
            model_id=command.provenance.model_id,
            status=command.status,
            created_at=command.created_at,
            human_readable=command.human_readable(),
        )


class ApiListPendingCommandsResponse(BaseModel):
    """A household's commands awaiting approval, oldest first."""

    commands: list[ApiPendingCommand]

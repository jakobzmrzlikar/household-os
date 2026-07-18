"""Request/response DTOs for the run_extraction command endpoint."""

from pydantic import BaseModel

from app.adapter.input.web.models.pending_command import ApiPendingCommand


class ApiRunExtractionRequest(BaseModel):
    """The capture to run receipt extraction on."""

    capture_id: str


class ApiRunExtractionResponse(BaseModel):
    """The commands staged by the extraction, awaiting approval."""

    commands: list[ApiPendingCommand]

"""Response DTOs for the create_capture command endpoint."""

from pydantic import BaseModel

from app.domain.models.capture import CaptureKind


class ApiCaptureResponse(BaseModel):
    """A created capture, as returned to the client."""

    id: str
    kind: CaptureKind

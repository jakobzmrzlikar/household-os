"""Use case: the create_capture command — store an upload and record a Capture."""

from datetime import UTC, datetime
from uuid import uuid4

from attrs import Attribute, define, field

from app.domain.models.capture import Capture, CaptureKind
from app.domain.ports.capture_repository import CaptureRepositoryPort
from app.domain.ports.media_storage import MediaStoragePort, MediaStoreRequest


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


def _require_non_empty(
    instance: object, attribute: "Attribute[bytes]", value: bytes
) -> None:
    """Reject empty file content.

    :param instance: The instance under validation (unused).
    :param attribute: The attrs field being validated.
    :param value: The value assigned to the field.
    :raises ValueError: When the uploaded content is empty.
    """
    if not value:
        raise ValueError(f"{attribute.name} must not be empty")


@define
class CreateCaptureRequest:
    """An uploaded file plus the household and member it belongs to.

    :param household_id: Household the capture belongs to.
    :param member_id: Member who submitted the capture.
    :param content: Raw bytes of the uploaded file.
    :param filename: Original client filename.
    :param content_type: MIME type of the uploaded file.
    """

    household_id: str = field(validator=_require_non_blank)
    member_id: str = field(validator=_require_non_blank)
    content: bytes = field(validator=_require_non_empty)
    filename: str
    content_type: str


@define(kw_only=True)
class CreateCaptureUsecase:
    """Use case: store an uploaded media file and persist a capture for it."""

    media_storage: MediaStoragePort
    capture_repository: CaptureRepositoryPort

    async def __call__(self, request: CreateCaptureRequest) -> Capture:
        """Execute the create_capture command.

        :param request: The uploaded file and its household/member ownership.
        :return: The persisted capture.
        :raises UnsupportedMediaTypeError: When the file is neither image nor audio.
        """
        kind = CaptureKind.from_content_type(request.content_type)
        media_path = await self.media_storage.store(
            MediaStoreRequest(
                content=request.content,
                filename=request.filename,
                content_type=request.content_type,
            )
        )
        capture = Capture(
            id=uuid4().hex,
            household_id=request.household_id,
            member_id=request.member_id,
            kind=kind,
            media_path=media_path,
            created_at=datetime.now(UTC),
        )
        await self.capture_repository.add(capture)
        return capture

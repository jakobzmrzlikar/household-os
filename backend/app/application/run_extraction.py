"""Use case: the run_extraction command — extract a capture, stage pending commands."""

import mimetypes
from datetime import UTC, datetime
from uuid import uuid4

from attrs import Attribute, define, field

from app.domain.models.capture import Capture, CaptureKind
from app.domain.models.pending_command import (
    CommandVerb,
    PendingCommand,
    PendingCommandStatus,
    Provenance,
)
from app.domain.models.receipt import Receipt
from app.domain.ports.capture_repository import CaptureRepositoryPort
from app.domain.ports.extraction_agent import (
    ExtractionAgentPort,
    ReceiptExtractionRequest,
)
from app.domain.ports.media_storage import MediaStoragePort
from app.domain.ports.pending_command_repository import PendingCommandRepositoryPort


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


class CaptureNotFoundError(LookupError):
    """Raised when the capture referenced by the command does not exist."""


class CaptureNotExtractableError(ValueError):
    """Raised when receipt extraction is requested for a non-photo capture."""


@define
class RunExtractionRequest:
    """The capture to run receipt extraction on.

    :param capture_id: Identifier of the photo capture to extract.
    """

    capture_id: str = field(validator=_require_non_blank)


@define(kw_only=True)
class RunExtractionUsecase:
    """Use case: extract a receipt capture and stage the proposed commands.

    Agent output is staged, never executed: the extraction result becomes inert
    ``PendingCommand`` rows awaiting member approval. No pantry or expense state
    is written here.
    """

    capture_repository: CaptureRepositoryPort
    media_storage: MediaStoragePort
    extraction_agent: ExtractionAgentPort
    pending_command_repository: PendingCommandRepositoryPort

    async def __call__(self, request: RunExtractionRequest) -> list[PendingCommand]:
        """Execute the run_extraction command.

        Stages one ``record_expense`` command (receipt total, paid by the
        capturing member, split equally) and one ``adjust_pantry_item`` command
        per receipt line item.

        :param request: The capture to extract.
        :return: The staged pending commands, expense first.
        :raises CaptureNotFoundError: When no capture has the requested id.
        :raises CaptureNotExtractableError: When the capture is not a photo.
        :raises ValueError: When the extracted receipt violates its invariants.
        """
        capture = await self.capture_repository.get(request.capture_id)
        if capture is None:
            raise CaptureNotFoundError(f"No capture with id {request.capture_id!r}")
        if capture.kind is not CaptureKind.PHOTO:
            raise CaptureNotExtractableError(
                f"Capture {capture.id!r} is {capture.kind.value}, not a photo"
            )
        image = await self.media_storage.load(capture.media_path)
        # The capture stores only a path; recover the MIME type from its
        # extension for the vision model, defaulting to JPEG (the phone
        # camera's format) when the extension is unknown.
        media_type = mimetypes.guess_type(capture.media_path)[0] or "image/jpeg"
        extraction = await self.extraction_agent.extract_receipt(
            ReceiptExtractionRequest(image=image, media_type=media_type)
        )
        commands = _stage_commands(capture, extraction.receipt, extraction.provenance)
        for command in commands:
            await self.pending_command_repository.add(command)
        return commands


def _stage_commands(
    capture: Capture, receipt: Receipt, provenance: Provenance
) -> list[PendingCommand]:
    """Materialize the receipt into inert pending commands.

    :param capture: The capture the receipt was extracted from.
    :param receipt: The extracted receipt.
    :param provenance: Which agent and model produced the extraction.
    :return: A ``record_expense`` command followed by one ``adjust_pantry_item``
        command per line item, all with status ``pending``.
    """
    created_at = datetime.now(UTC)
    expense = PendingCommand(
        id=uuid4().hex,
        household_id=capture.household_id,
        capture_id=capture.id,
        verb=CommandVerb.RECORD_EXPENSE,
        payload={
            "amount": receipt.total,
            "currency": receipt.currency,
            "merchant": receipt.merchant,
            "payer_member_id": capture.member_id,
            "split": "equal",
        },
        provenance=provenance,
        status=PendingCommandStatus.PENDING,
        created_at=created_at,
    )
    pantry_adjustments = [
        PendingCommand(
            id=uuid4().hex,
            household_id=capture.household_id,
            capture_id=capture.id,
            verb=CommandVerb.ADJUST_PANTRY_ITEM,
            payload={
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
            },
            provenance=provenance,
            status=PendingCommandStatus.PENDING,
            created_at=created_at,
        )
        for item in receipt.line_items
    ]
    return [expense, *pantry_adjustments]

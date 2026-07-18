"""Use case: the run_extraction command — extract a capture, stage pending commands."""

import mimetypes
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from attrs import Attribute, define, field

from app.domain.models.capture import Capture, CaptureKind
from app.domain.models.pantry_intent import PantryIntent
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
from app.domain.ports.pantry_intent_agent import (
    PantryIntentAgentPort,
    PantryIntentExtractionRequest,
)
from app.domain.ports.speech_transcription import (
    SpeechTranscriptionPort,
    SpeechTranscriptionRequest,
)
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


class CaptureNotFoundError(LookupError):
    """Raised when the capture referenced by the command does not exist."""


@define
class RunExtractionRequest:
    """The capture to run extraction on.

    :param capture_id: Identifier of the capture to extract.
    """

    capture_id: str = field(validator=_require_non_blank)


@define(kw_only=True)
class RunExtractionUsecase:
    """Use case: extract a capture and stage the proposed commands.

    Photo captures go through receipt extraction; audio captures are
    transcribed and mined for pantry intents. Either way, agent output is
    staged, never executed: the extraction result becomes inert
    ``PendingCommand`` rows awaiting member approval. No pantry or expense
    state is written here.
    """

    capture_repository: CaptureRepositoryPort
    media_storage: MediaStoragePort
    extraction_agent: ExtractionAgentPort
    speech_transcription: SpeechTranscriptionPort
    pantry_intent_agent: PantryIntentAgentPort
    unit_of_work_factory: Callable[[], UnitOfWorkPort]

    async def __call__(self, request: RunExtractionRequest) -> list[PendingCommand]:
        """Execute the run_extraction command.

        For a photo, stages one ``record_expense`` command (receipt total,
        paid by the capturing member) and one ``adjust_pantry_item`` command
        per receipt line item. For a voice note, stages one
        ``adjust_pantry_item`` command per pantry intent heard in the
        transcript. All commands of one run are staged in one transaction.

        :param request: The capture to extract.
        :return: The staged pending commands; may be empty for a voice note
            that mentions no pantry items.
        :raises CaptureNotFoundError: When no capture has the requested id.
        :raises ValueError: When the extracted data violates its invariants.
        """
        capture = await self.capture_repository.get(request.capture_id)
        if capture is None:
            raise CaptureNotFoundError(f"No capture with id {request.capture_id!r}")
        media = await self.media_storage.load(capture.media_path)
        if capture.kind is CaptureKind.PHOTO:
            commands = await self._extract_receipt(capture, media)
        else:
            commands = await self._extract_voice_note(capture, media)
        async with self.unit_of_work_factory() as unit_of_work:
            for command in commands:
                await unit_of_work.pending_commands.add(command)
        return commands

    async def _extract_receipt(
        self, capture: Capture, image: bytes
    ) -> list[PendingCommand]:
        """Run receipt extraction on a photo capture.

        :param capture: The photo capture being extracted.
        :param image: The stored photo bytes.
        :return: The staged-but-unpersisted commands, expense first.
        """
        # The capture stores only a path; recover the MIME type from its
        # extension for the vision model, defaulting to JPEG (the phone
        # camera's format) when the extension is unknown.
        media_type = mimetypes.guess_type(capture.media_path)[0] or "image/jpeg"
        extraction = await self.extraction_agent.extract_receipt(
            ReceiptExtractionRequest(image=image, media_type=media_type)
        )
        return _stage_receipt_commands(
            capture, extraction.receipt, extraction.provenance
        )

    async def _extract_voice_note(
        self, capture: Capture, audio: bytes
    ) -> list[PendingCommand]:
        """Transcribe an audio capture and mine the transcript for intents.

        :param capture: The audio capture being extracted.
        :param audio: The stored recording bytes.
        :return: The staged-but-unpersisted pantry adjustment commands.
        """
        # As with photos, the MIME type is recovered from the stored path;
        # phone voice notes are m4a, so audio/mp4 is the fallback.
        content_type = mimetypes.guess_type(capture.media_path)[0] or "audio/mp4"
        transcript = await self.speech_transcription.transcribe(
            SpeechTranscriptionRequest(audio=audio, content_type=content_type)
        )
        extraction = await self.pantry_intent_agent.extract_intents(
            PantryIntentExtractionRequest(transcript=transcript)
        )
        return _stage_intent_commands(
            capture, extraction.intents, extraction.provenance
        )


def _stage_receipt_commands(
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
            # Fully materialized split, as the record_expense verb requires.
            # Without a member registry to divide across, the whole amount
            # falls to the capturing member who paid.
            "split": {capture.member_id: receipt.total},
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


def _stage_intent_commands(
    capture: Capture, intents: tuple[PantryIntent, ...], provenance: Provenance
) -> list[PendingCommand]:
    """Materialize voice-note pantry intents into inert pending commands.

    :param capture: The audio capture the intents were extracted from.
    :param intents: The pantry intents heard in the transcript.
    :param provenance: Which agent and model produced the extraction,
        transcript included.
    :return: One ``adjust_pantry_item`` command per intent, status ``pending``.
    """
    created_at = datetime.now(UTC)
    return [
        PendingCommand(
            id=uuid4().hex,
            household_id=capture.household_id,
            capture_id=capture.id,
            verb=CommandVerb.ADJUST_PANTRY_ITEM,
            payload=_intent_payload(intent),
            provenance=provenance,
            status=PendingCommandStatus.PENDING,
            created_at=created_at,
        )
        for intent in intents
    ]


def _intent_payload(intent: PantryIntent) -> dict[str, object]:
    """Build the adjust_pantry_item verb arguments for one intent.

    :param intent: The pantry intent to materialize.
    :return: A payload the verb accepts: the delta form carries ``quantity``,
        the depletion form carries ``out_of_stock``; the optional note rides
        along for the approval UI.
    """
    payload: dict[str, object] = {"name": intent.name}
    if intent.quantity_delta is not None:
        payload["quantity"] = intent.quantity_delta
    if intent.out_of_stock:
        payload["out_of_stock"] = True
    if intent.note is not None:
        payload["note"] = intent.note
    return payload

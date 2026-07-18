"""Unit tests for the run_extraction use case."""

from datetime import UTC, datetime

import pytest

from app.adapter.output.mock_capture_repository import MockCaptureRepository
from app.adapter.output.mock_extraction_agent import (
    AGENT_NAME,
    MODEL_ID,
    MockExtractionAgent,
)
from app.adapter.output.mock_media_storage import MockMediaStorage
from app.adapter.output.mock_pantry_intent_agent import (
    AGENT_NAME as INTENT_AGENT_NAME,
)
from app.adapter.output.mock_pantry_intent_agent import MockPantryIntentAgent
from app.adapter.output.mock_pantry_item_repository import MockPantryItemRepository
from app.adapter.output.mock_pending_command_repository import (
    MockPendingCommandRepository,
)
from app.adapter.output.mock_speech_transcription import (
    TRANSCRIPT,
    MockSpeechTranscription,
)
from app.adapter.output.mock_unit_of_work import MockUnitOfWork
from app.application.run_extraction import (
    CaptureNotFoundError,
    RunExtractionRequest,
    RunExtractionUsecase,
)
from app.domain.models.capture import Capture, CaptureKind
from app.domain.models.pending_command import CommandVerb, PendingCommandStatus
from app.domain.ports.media_storage import MediaStoreRequest


@pytest.fixture
def capture_repository() -> MockCaptureRepository:
    """Mock repository recording captures in memory."""
    return MockCaptureRepository()


@pytest.fixture
def media_storage() -> MockMediaStorage:
    """Mock storage recording file bytes in memory."""
    return MockMediaStorage()


@pytest.fixture
def extraction_agent() -> MockExtractionAgent:
    """Mock agent answering with a fixed grocery receipt."""
    return MockExtractionAgent()


@pytest.fixture
def speech_transcription() -> MockSpeechTranscription:
    """Mock transcription answering with a fixed voice-note transcript."""
    return MockSpeechTranscription()


@pytest.fixture
def pantry_intent_agent() -> MockPantryIntentAgent:
    """Mock agent answering with fixed out-of-stock pantry intents."""
    return MockPantryIntentAgent()


@pytest.fixture
def pending_command_repository() -> MockPendingCommandRepository:
    """Mock repository recording staged commands in memory."""
    return MockPendingCommandRepository()


@pytest.fixture
def unit_of_work(
    pending_command_repository: MockPendingCommandRepository,
) -> MockUnitOfWork:
    """Mock unit of work exposing the in-memory pending command repository."""
    return MockUnitOfWork(pending_commands=pending_command_repository)


@pytest.fixture
def usecase(
    capture_repository: MockCaptureRepository,
    media_storage: MockMediaStorage,
    extraction_agent: MockExtractionAgent,
    speech_transcription: MockSpeechTranscription,
    pantry_intent_agent: MockPantryIntentAgent,
    unit_of_work: MockUnitOfWork,
) -> RunExtractionUsecase:
    """Use case under test, wired to the in-memory mocks."""
    return RunExtractionUsecase(
        capture_repository=capture_repository,
        media_storage=media_storage,
        extraction_agent=extraction_agent,
        speech_transcription=speech_transcription,
        pantry_intent_agent=pantry_intent_agent,
        unit_of_work_factory=lambda: unit_of_work,
    )


async def _add_photo_capture(
    capture_repository: MockCaptureRepository, media_storage: MockMediaStorage
) -> Capture:
    """Store fake receipt-photo bytes and record a photo capture over them."""
    media_path = await media_storage.store(
        MediaStoreRequest(
            content=b"fake-jpeg", filename="receipt.jpg", content_type="image/jpeg"
        )
    )
    capture = Capture(
        id="cap-1",
        household_id="hh-1",
        member_id="mem-1",
        kind=CaptureKind.PHOTO,
        media_path=media_path,
        created_at=datetime.now(UTC),
    )
    await capture_repository.add(capture)
    return capture


async def _add_audio_capture(
    capture_repository: MockCaptureRepository, media_storage: MockMediaStorage
) -> Capture:
    """Store fake voice-note bytes and record an audio capture over them."""
    media_path = await media_storage.store(
        MediaStoreRequest(
            content=b"fake-m4a", filename="note.m4a", content_type="audio/mp4"
        )
    )
    capture = Capture(
        id="cap-audio",
        household_id="hh-1",
        member_id="mem-1",
        kind=CaptureKind.AUDIO,
        media_path=media_path,
        created_at=datetime.now(UTC),
    )
    await capture_repository.add(capture)
    return capture


async def test_run_extraction_should_stage_expense_and_pantry_when_capture_is_photo(
    usecase: RunExtractionUsecase,
    capture_repository: MockCaptureRepository,
    media_storage: MockMediaStorage,
    extraction_agent: MockExtractionAgent,
) -> None:
    capture = await _add_photo_capture(capture_repository, media_storage)
    receipt = extraction_agent.receipt

    commands = await usecase(RunExtractionRequest(capture_id=capture.id))

    expense, *pantry = commands
    assert expense.verb is CommandVerb.RECORD_EXPENSE
    assert expense.payload == {
        "amount": receipt.total,
        "currency": receipt.currency,
        "merchant": receipt.merchant,
        "payer_member_id": capture.member_id,
        "split": {capture.member_id: receipt.total},
    }
    assert [command.verb for command in pantry] == [
        CommandVerb.ADJUST_PANTRY_ITEM
    ] * len(receipt.line_items)
    assert [command.payload for command in pantry] == [
        {"name": item.name, "quantity": item.quantity, "unit": item.unit}
        for item in receipt.line_items
    ]


async def test_run_extraction_should_only_stage_pending_rows_when_extraction_runs(
    usecase: RunExtractionUsecase,
    capture_repository: MockCaptureRepository,
    media_storage: MockMediaStorage,
    pending_command_repository: MockPendingCommandRepository,
) -> None:
    capture = await _add_photo_capture(capture_repository, media_storage)

    commands = await usecase(RunExtractionRequest(capture_id=capture.id))

    # Staged, never executed: every command sits in the pending repository with
    # status pending, scoped to the capture's household and capture.
    assert pending_command_repository.commands == commands
    assert all(command.status is PendingCommandStatus.PENDING for command in commands)
    assert all(command.household_id == capture.household_id for command in commands)
    assert all(command.capture_id == capture.id for command in commands)


async def test_run_extraction_should_carry_provenance_when_commands_staged(
    usecase: RunExtractionUsecase,
    capture_repository: MockCaptureRepository,
    media_storage: MockMediaStorage,
) -> None:
    capture = await _add_photo_capture(capture_repository, media_storage)

    commands = await usecase(RunExtractionRequest(capture_id=capture.id))

    assert all(command.provenance.agent_name == AGENT_NAME for command in commands)
    assert all(command.provenance.model_id == MODEL_ID for command in commands)


async def test_run_extraction_should_send_stored_image_when_agent_invoked(
    usecase: RunExtractionUsecase,
    capture_repository: MockCaptureRepository,
    media_storage: MockMediaStorage,
    extraction_agent: MockExtractionAgent,
) -> None:
    capture = await _add_photo_capture(capture_repository, media_storage)

    await usecase(RunExtractionRequest(capture_id=capture.id))

    assert [request.image for request in extraction_agent.requests] == [b"fake-jpeg"]
    assert extraction_agent.requests[0].media_type == "image/jpeg"


async def test_run_extraction_should_stage_pantry_adjustments_when_capture_is_audio(
    usecase: RunExtractionUsecase,
    capture_repository: MockCaptureRepository,
    media_storage: MockMediaStorage,
    pantry_intent_agent: MockPantryIntentAgent,
) -> None:
    capture = await _add_audio_capture(capture_repository, media_storage)

    commands = await usecase(RunExtractionRequest(capture_id=capture.id))

    assert [command.verb for command in commands] == [
        CommandVerb.ADJUST_PANTRY_ITEM
    ] * len(pantry_intent_agent.intents)
    assert [command.payload for command in commands] == [
        {"name": intent.name, "out_of_stock": True}
        for intent in pantry_intent_agent.intents
    ]
    assert all(command.capture_id == capture.id for command in commands)


async def test_run_extraction_should_stage_inert_rows_when_capture_is_audio(
    usecase: RunExtractionUsecase,
    capture_repository: MockCaptureRepository,
    media_storage: MockMediaStorage,
    pending_command_repository: MockPendingCommandRepository,
    unit_of_work: MockUnitOfWork,
) -> None:
    capture = await _add_audio_capture(capture_repository, media_storage)

    commands = await usecase(RunExtractionRequest(capture_id=capture.id))

    # Staged, never executed: the commands sit pending and no pantry state
    # was written anywhere.
    assert pending_command_repository.commands == commands
    assert all(command.status is PendingCommandStatus.PENDING for command in commands)
    assert isinstance(unit_of_work.pantry_items, MockPantryItemRepository)
    assert unit_of_work.pantry_items.items == {}


async def test_run_extraction_should_carry_transcript_provenance_when_capture_is_audio(
    usecase: RunExtractionUsecase,
    capture_repository: MockCaptureRepository,
    media_storage: MockMediaStorage,
) -> None:
    capture = await _add_audio_capture(capture_repository, media_storage)

    commands = await usecase(RunExtractionRequest(capture_id=capture.id))

    assert all(
        command.provenance.agent_name == INTENT_AGENT_NAME for command in commands
    )
    assert all(command.provenance.transcript == TRANSCRIPT for command in commands)


async def test_run_extraction_should_send_stored_audio_when_transcription_invoked(
    usecase: RunExtractionUsecase,
    capture_repository: MockCaptureRepository,
    media_storage: MockMediaStorage,
    speech_transcription: MockSpeechTranscription,
    pantry_intent_agent: MockPantryIntentAgent,
) -> None:
    capture = await _add_audio_capture(capture_repository, media_storage)

    await usecase(RunExtractionRequest(capture_id=capture.id))

    assert [request.audio for request in speech_transcription.requests] == [b"fake-m4a"]
    assert speech_transcription.requests[0].content_type.startswith("audio/")
    # The transcript flows on into the intent agent unchanged.
    assert [request.transcript for request in pantry_intent_agent.requests] == [
        TRANSCRIPT
    ]


async def test_run_extraction_should_stage_nothing_when_voice_note_has_no_intents(
    capture_repository: MockCaptureRepository,
    media_storage: MockMediaStorage,
    pending_command_repository: MockPendingCommandRepository,
) -> None:
    usecase = RunExtractionUsecase(
        capture_repository=capture_repository,
        media_storage=media_storage,
        extraction_agent=MockExtractionAgent(),
        speech_transcription=MockSpeechTranscription(),
        pantry_intent_agent=MockPantryIntentAgent(intents=()),
        unit_of_work_factory=lambda: MockUnitOfWork(
            pending_commands=pending_command_repository
        ),
    )
    capture = await _add_audio_capture(capture_repository, media_storage)

    commands = await usecase(RunExtractionRequest(capture_id=capture.id))

    assert commands == []
    assert pending_command_repository.commands == []


async def test_run_extraction_should_raise_error_when_capture_missing(
    usecase: RunExtractionUsecase,
    pending_command_repository: MockPendingCommandRepository,
) -> None:
    with pytest.raises(CaptureNotFoundError):
        await usecase(RunExtractionRequest(capture_id="missing"))

    assert pending_command_repository.commands == []


def test_run_extraction_request_should_raise_error_when_capture_id_blank() -> None:
    with pytest.raises(ValueError, match="capture_id"):
        RunExtractionRequest(capture_id="   ")

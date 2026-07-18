"""Unit tests for the create_capture use case."""

import pytest

from app.adapter.output.mock_capture_repository import MockCaptureRepository
from app.adapter.output.mock_extraction_agent import MockExtractionAgent
from app.adapter.output.mock_media_storage import MockMediaStorage
from app.adapter.output.mock_pantry_intent_agent import MockPantryIntentAgent
from app.adapter.output.mock_pending_command_repository import (
    MockPendingCommandRepository,
)
from app.adapter.output.mock_speech_transcription import MockSpeechTranscription
from app.adapter.output.mock_unit_of_work import MockUnitOfWork
from app.application.create_capture import CreateCaptureRequest, CreateCaptureUsecase
from app.application.run_extraction import RunExtractionUsecase
from app.domain.models.capture import CaptureKind, UnsupportedMediaTypeError
from app.domain.models.pending_command import CommandVerb
from app.domain.ports.extraction_agent import (
    ExtractionAgentPort,
    ReceiptExtractionRequest,
    ReceiptExtractionResponse,
)


class ExplodingExtractionAgent(ExtractionAgentPort):
    """Extraction agent stub that fails every request."""

    async def extract_receipt(
        self, request: ReceiptExtractionRequest
    ) -> ReceiptExtractionResponse:
        """Fail unconditionally.

        :param request: The extraction request (unused).
        :raises RuntimeError: Always.
        """
        raise RuntimeError("model unavailable")


@pytest.fixture
def capture_repository() -> MockCaptureRepository:
    """Mock repository recording captures in memory."""
    return MockCaptureRepository()


@pytest.fixture
def media_storage() -> MockMediaStorage:
    """Mock storage recording file bytes in memory."""
    return MockMediaStorage()


@pytest.fixture
def pending_command_repository() -> MockPendingCommandRepository:
    """Mock repository recording commands staged by the automatic extraction."""
    return MockPendingCommandRepository()


@pytest.fixture
def usecase(
    capture_repository: MockCaptureRepository,
    media_storage: MockMediaStorage,
    pending_command_repository: MockPendingCommandRepository,
) -> CreateCaptureUsecase:
    """Use case under test, wired to the in-memory mocks."""
    run_extraction_usecase = RunExtractionUsecase(
        capture_repository=capture_repository,
        media_storage=media_storage,
        extraction_agent=MockExtractionAgent(),
        speech_transcription=MockSpeechTranscription(),
        pantry_intent_agent=MockPantryIntentAgent(),
        unit_of_work_factory=lambda: MockUnitOfWork(
            pending_commands=pending_command_repository
        ),
    )
    return CreateCaptureUsecase(
        media_storage=media_storage,
        capture_repository=capture_repository,
        run_extraction_usecase=run_extraction_usecase,
    )


def _request(content_type: str, filename: str = "note.bin") -> CreateCaptureRequest:
    return CreateCaptureRequest(
        household_id="hh-1",
        member_id="mem-1",
        content=b"payload",
        filename=filename,
        content_type=content_type,
    )


async def test_create_capture_should_persist_photo_capture_when_image_uploaded(
    usecase: CreateCaptureUsecase,
    capture_repository: MockCaptureRepository,
    media_storage: MockMediaStorage,
) -> None:
    capture = await usecase(_request("image/jpeg", filename="receipt.jpg"))

    assert capture.kind is CaptureKind.PHOTO
    assert capture_repository.captures == [capture]
    assert media_storage.stored[capture.media_path] == b"payload"


async def test_create_capture_should_persist_audio_capture_when_audio_uploaded(
    usecase: CreateCaptureUsecase, capture_repository: MockCaptureRepository
) -> None:
    capture = await usecase(_request("audio/m4a", filename="note.m4a"))

    assert capture.kind is CaptureKind.AUDIO
    assert capture_repository.captures == [capture]


async def test_create_capture_should_stage_commands_when_photo_uploaded(
    usecase: CreateCaptureUsecase,
    pending_command_repository: MockPendingCommandRepository,
) -> None:
    capture = await usecase(_request("image/jpeg", filename="receipt.jpg"))

    commands = await pending_command_repository.list_pending("hh-1")
    assert commands
    assert all(command.capture_id == capture.id for command in commands)


async def test_create_capture_should_stage_pantry_commands_when_audio_uploaded(
    usecase: CreateCaptureUsecase,
    pending_command_repository: MockPendingCommandRepository,
) -> None:
    capture = await usecase(_request("audio/m4a", filename="note.m4a"))

    # Voice extraction ran automatically: transcription plus intent extraction
    # staged one pantry adjustment per intent, nothing more.
    commands = pending_command_repository.commands
    assert commands
    assert all(command.verb is CommandVerb.ADJUST_PANTRY_ITEM for command in commands)
    assert all(command.capture_id == capture.id for command in commands)
    assert all(command.provenance.transcript for command in commands)


async def test_create_capture_should_persist_capture_when_extraction_fails(
    capture_repository: MockCaptureRepository,
    media_storage: MockMediaStorage,
    pending_command_repository: MockPendingCommandRepository,
) -> None:
    run_extraction_usecase = RunExtractionUsecase(
        capture_repository=capture_repository,
        media_storage=media_storage,
        extraction_agent=ExplodingExtractionAgent(),
        speech_transcription=MockSpeechTranscription(),
        pantry_intent_agent=MockPantryIntentAgent(),
        unit_of_work_factory=lambda: MockUnitOfWork(
            pending_commands=pending_command_repository
        ),
    )
    usecase = CreateCaptureUsecase(
        media_storage=media_storage,
        capture_repository=capture_repository,
        run_extraction_usecase=run_extraction_usecase,
    )

    capture = await usecase(_request("image/jpeg", filename="receipt.jpg"))

    # The upload survives the failed extraction; nothing is staged.
    assert capture_repository.captures == [capture]
    assert pending_command_repository.commands == []


async def test_create_capture_should_raise_error_when_content_type_unsupported(
    usecase: CreateCaptureUsecase, capture_repository: MockCaptureRepository
) -> None:
    with pytest.raises(UnsupportedMediaTypeError):
        await usecase(_request("text/plain"))

    assert capture_repository.captures == []


def test_create_capture_request_should_raise_error_when_household_id_blank() -> None:
    with pytest.raises(ValueError, match="household_id"):
        CreateCaptureRequest(
            household_id="  ",
            member_id="mem-1",
            content=b"payload",
            filename="receipt.jpg",
            content_type="image/jpeg",
        )


def test_create_capture_request_should_raise_error_when_content_empty() -> None:
    with pytest.raises(ValueError, match="content"):
        CreateCaptureRequest(
            household_id="hh-1",
            member_id="mem-1",
            content=b"",
            filename="receipt.jpg",
            content_type="image/jpeg",
        )

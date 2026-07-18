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
from app.adapter.output.mock_pending_command_repository import (
    MockPendingCommandRepository,
)
from app.application.run_extraction import (
    CaptureNotExtractableError,
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
def pending_command_repository() -> MockPendingCommandRepository:
    """Mock repository recording staged commands in memory."""
    return MockPendingCommandRepository()


@pytest.fixture
def usecase(
    capture_repository: MockCaptureRepository,
    media_storage: MockMediaStorage,
    extraction_agent: MockExtractionAgent,
    pending_command_repository: MockPendingCommandRepository,
) -> RunExtractionUsecase:
    """Use case under test, wired to the in-memory mocks."""
    return RunExtractionUsecase(
        capture_repository=capture_repository,
        media_storage=media_storage,
        extraction_agent=extraction_agent,
        pending_command_repository=pending_command_repository,
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
        "split": "equal",
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


async def test_run_extraction_should_raise_error_when_capture_missing(
    usecase: RunExtractionUsecase,
    pending_command_repository: MockPendingCommandRepository,
) -> None:
    with pytest.raises(CaptureNotFoundError):
        await usecase(RunExtractionRequest(capture_id="missing"))

    assert pending_command_repository.commands == []


async def test_run_extraction_should_raise_error_when_capture_is_audio(
    usecase: RunExtractionUsecase,
    capture_repository: MockCaptureRepository,
    pending_command_repository: MockPendingCommandRepository,
) -> None:
    await capture_repository.add(
        Capture(
            id="cap-audio",
            household_id="hh-1",
            member_id="mem-1",
            kind=CaptureKind.AUDIO,
            media_path="note.m4a",
            created_at=datetime.now(UTC),
        )
    )

    with pytest.raises(CaptureNotExtractableError):
        await usecase(RunExtractionRequest(capture_id="cap-audio"))

    assert pending_command_repository.commands == []


def test_run_extraction_request_should_raise_error_when_capture_id_blank() -> None:
    with pytest.raises(ValueError, match="capture_id"):
        RunExtractionRequest(capture_id="   ")

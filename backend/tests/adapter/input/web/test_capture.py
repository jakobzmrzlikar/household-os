"""Endpoint tests for the create_capture command."""

import pytest
from fastapi.testclient import TestClient

from app.adapter.output.mock_capture_repository import MockCaptureRepository
from app.adapter.output.mock_extraction_agent import MockExtractionAgent
from app.adapter.output.mock_media_storage import MockMediaStorage
from app.adapter.output.mock_pantry_intent_agent import MockPantryIntentAgent
from app.adapter.output.mock_pending_command_repository import (
    MockPendingCommandRepository,
)
from app.adapter.output.mock_speech_transcription import MockSpeechTranscription
from app.adapter.output.mock_unit_of_work import MockUnitOfWork
from app.infrastructure.app import create_app
from app.infrastructure.container import Container


@pytest.fixture
def capture_repository() -> MockCaptureRepository:
    """Mock repository recording captures in memory."""
    return MockCaptureRepository()


@pytest.fixture
def pending_command_repository() -> MockPendingCommandRepository:
    """Mock repository recording commands staged by the automatic extraction."""
    return MockPendingCommandRepository()


@pytest.fixture
def client(
    capture_repository: MockCaptureRepository,
    pending_command_repository: MockPendingCommandRepository,
) -> TestClient:
    """App client with storage, persistence, and the agent overridden by mocks.

    Built per-test (not at module import) so this container is the most recently
    wired one when the request runs.
    """
    app = create_app()
    container: Container = app.state.container
    # dependency_injector's stubs leave Provider.override partially generic.
    container.media_storage.override(  # pyright: ignore[reportUnknownMemberType]
        MockMediaStorage()
    )
    container.capture_repository.override(  # pyright: ignore[reportUnknownMemberType]
        capture_repository
    )
    container.extraction_agent.override(  # pyright: ignore[reportUnknownMemberType]
        MockExtractionAgent()
    )
    container.speech_transcription.override(  # pyright: ignore[reportUnknownMemberType]
        MockSpeechTranscription()
    )
    container.pantry_intent_agent.override(  # pyright: ignore[reportUnknownMemberType]
        MockPantryIntentAgent()
    )
    container.unit_of_work.override(  # pyright: ignore[reportUnknownMemberType]
        MockUnitOfWork(pending_commands=pending_command_repository)
    )
    return TestClient(app)


def test_create_capture_endpoint_should_return_201_when_photo_uploaded(
    client: TestClient, capture_repository: MockCaptureRepository
) -> None:
    response = client.post(
        "/create_capture",
        data={"household_id": "hh-1", "member_id": "mem-1"},
        files={"file": ("receipt.jpg", b"fake-jpeg", "image/jpeg")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "photo"
    assert [capture.id for capture in capture_repository.captures] == [body["id"]]


def test_create_capture_endpoint_should_stage_commands_when_photo_uploaded(
    client: TestClient, pending_command_repository: MockPendingCommandRepository
) -> None:
    response = client.post(
        "/create_capture",
        data={"household_id": "hh-1", "member_id": "mem-1"},
        files={"file": ("receipt.jpg", b"fake-jpeg", "image/jpeg")},
    )

    # Extraction ran automatically in-process: the proposed commands are
    # staged for approval without a separate /run_extraction call.
    commands = pending_command_repository.commands
    assert commands
    assert all(command.capture_id == response.json()["id"] for command in commands)


def test_create_capture_endpoint_should_return_201_when_audio_uploaded(
    client: TestClient,
) -> None:
    response = client.post(
        "/create_capture",
        data={"household_id": "hh-1", "member_id": "mem-1"},
        files={"file": ("note.m4a", b"fake-m4a", "audio/m4a")},
    )

    assert response.status_code == 201
    assert response.json()["kind"] == "audio"


def test_create_capture_endpoint_should_stage_commands_when_audio_uploaded(
    client: TestClient, pending_command_repository: MockPendingCommandRepository
) -> None:
    response = client.post(
        "/create_capture",
        data={"household_id": "hh-1", "member_id": "mem-1"},
        files={"file": ("note.m4a", b"fake-m4a", "audio/m4a")},
    )

    # Voice extraction ran automatically in-process: transcription plus intent
    # extraction staged pantry adjustments for approval.
    commands = pending_command_repository.commands
    assert commands
    assert all(command.capture_id == response.json()["id"] for command in commands)
    assert all(command.provenance.transcript for command in commands)


def test_create_capture_endpoint_should_return_415_when_file_not_media(
    client: TestClient, capture_repository: MockCaptureRepository
) -> None:
    response = client.post(
        "/create_capture",
        data={"household_id": "hh-1", "member_id": "mem-1"},
        files={"file": ("notes.txt", b"text", "text/plain")},
    )

    assert response.status_code == 415
    assert capture_repository.captures == []


def test_create_capture_endpoint_should_return_422_when_household_id_blank(
    client: TestClient,
) -> None:
    response = client.post(
        "/create_capture",
        data={"household_id": "   ", "member_id": "mem-1"},
        files={"file": ("receipt.jpg", b"fake-jpeg", "image/jpeg")},
    )

    assert response.status_code == 422

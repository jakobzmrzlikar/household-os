"""Endpoint tests for the run_extraction command."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.adapter.output.mock_capture_repository import MockCaptureRepository
from app.adapter.output.mock_extraction_agent import MockExtractionAgent
from app.adapter.output.mock_media_storage import MockMediaStorage
from app.adapter.output.mock_pending_command_repository import (
    MockPendingCommandRepository,
)
from app.domain.models.capture import Capture, CaptureKind
from app.infrastructure.app import create_app
from app.infrastructure.container import Container


@pytest.fixture
def pending_command_repository() -> MockPendingCommandRepository:
    """Mock repository recording staged commands in memory."""
    return MockPendingCommandRepository()


@pytest.fixture
def client(pending_command_repository: MockPendingCommandRepository) -> TestClient:
    """App client with all ports overridden by in-memory mocks.

    The capture repository is pre-seeded with a photo capture (``cap-1``) whose
    bytes sit in the mock media storage under ``receipt.jpg``.
    """
    capture_repository = MockCaptureRepository()
    capture_repository.captures.append(
        Capture(
            id="cap-1",
            household_id="hh-1",
            member_id="mem-1",
            kind=CaptureKind.PHOTO,
            media_path="receipt.jpg",
            created_at=datetime.now(UTC),
        )
    )
    media_storage = MockMediaStorage()
    media_storage.stored["receipt.jpg"] = b"fake-jpeg"

    app = create_app()
    container: Container = app.state.container
    # dependency_injector's stubs leave Provider.override partially generic.
    container.capture_repository.override(  # pyright: ignore[reportUnknownMemberType]
        capture_repository
    )
    container.media_storage.override(  # pyright: ignore[reportUnknownMemberType]
        media_storage
    )
    container.extraction_agent.override(  # pyright: ignore[reportUnknownMemberType]
        MockExtractionAgent()
    )
    container.pending_command_repository.override(  # pyright: ignore[reportUnknownMemberType]
        pending_command_repository
    )
    return TestClient(app)


def test_run_extraction_endpoint_should_return_staged_commands_when_capture_exists(
    client: TestClient, pending_command_repository: MockPendingCommandRepository
) -> None:
    response = client.post("/run_extraction", json={"capture_id": "cap-1"})

    assert response.status_code == 201
    commands = response.json()["commands"]
    assert [command["verb"] for command in commands[:1]] == ["record_expense"]
    assert all(command["verb"] == "adjust_pantry_item" for command in commands[1:])
    assert all(command["status"] == "pending" for command in commands)
    assert all(command["agent_name"] and command["model_id"] for command in commands)
    assert all(command["human_readable"] for command in commands)
    assert [command.id for command in pending_command_repository.commands] == [
        command["id"] for command in commands
    ]


def test_run_extraction_endpoint_should_return_404_when_capture_unknown(
    client: TestClient, pending_command_repository: MockPendingCommandRepository
) -> None:
    response = client.post("/run_extraction", json={"capture_id": "missing"})

    assert response.status_code == 404
    assert pending_command_repository.commands == []

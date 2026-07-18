"""Endpoint tests for the list_pending_commands query."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.adapter.output.mock_pending_command_repository import (
    MockPendingCommandRepository,
)
from app.domain.models.pending_command import (
    CommandVerb,
    PendingCommand,
    PendingCommandStatus,
    Provenance,
)
from app.infrastructure.app import create_app
from app.infrastructure.container import Container


@pytest.fixture
def pending_command_repository() -> MockPendingCommandRepository:
    """Mock repository pre-seeded with one pending expense command."""
    repository = MockPendingCommandRepository()
    repository.commands.append(
        PendingCommand(
            id="cmd-1",
            household_id="hh-1",
            capture_id="cap-1",
            verb=CommandVerb.RECORD_EXPENSE,
            payload={
                "amount": 23.70,
                "currency": "EUR",
                "merchant": "Mercator",
                "payer_member_id": "mem-1",
                "split": "equal",
            },
            provenance=Provenance(agent_name="mock_extraction_agent", model_id="mock"),
            status=PendingCommandStatus.PENDING,
            created_at=datetime.now(UTC),
        )
    )
    return repository


@pytest.fixture
def client(pending_command_repository: MockPendingCommandRepository) -> TestClient:
    """App client with persistence overridden by the in-memory mock."""
    app = create_app()
    container: Container = app.state.container
    # dependency_injector's stubs leave Provider.override partially generic.
    container.pending_command_repository.override(  # pyright: ignore[reportUnknownMemberType]
        pending_command_repository
    )
    return TestClient(app)


def test_list_pending_commands_endpoint_should_return_summaries_when_commands_pending(
    client: TestClient,
) -> None:
    response = client.get("/list_pending_commands", params={"household_id": "hh-1"})

    assert response.status_code == 200
    commands = response.json()["commands"]
    assert [command["id"] for command in commands] == ["cmd-1"]
    assert commands[0]["human_readable"] == (
        "Record expense of 23.7 EUR at Mercator, paid by mem-1, split equally"
    )


def test_list_pending_commands_endpoint_should_return_empty_when_household_has_none(
    client: TestClient,
) -> None:
    response = client.get("/list_pending_commands", params={"household_id": "hh-2"})

    assert response.status_code == 200
    assert response.json()["commands"] == []


def test_list_pending_commands_endpoint_should_return_422_when_household_id_blank(
    client: TestClient,
) -> None:
    response = client.get("/list_pending_commands", params={"household_id": "   "})

    assert response.status_code == 422

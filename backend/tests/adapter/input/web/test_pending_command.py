"""Endpoint tests for the pending command endpoints (list, approve, reject)."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.adapter.output.mock_expense_entry_repository import (
    MockExpenseEntryRepository,
)
from app.adapter.output.mock_pending_command_repository import (
    MockPendingCommandRepository,
)
from app.adapter.output.mock_unit_of_work import MockUnitOfWork
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
                "split": {"mem-1": 23.70},
            },
            provenance=Provenance(agent_name="mock_extraction_agent", model_id="mock"),
            status=PendingCommandStatus.PENDING,
            created_at=datetime.now(UTC),
        )
    )
    return repository


@pytest.fixture
def expense_entry_repository() -> MockExpenseEntryRepository:
    """Mock repository recording executed expense entries."""
    return MockExpenseEntryRepository()


@pytest.fixture
def client(
    pending_command_repository: MockPendingCommandRepository,
    expense_entry_repository: MockExpenseEntryRepository,
) -> TestClient:
    """App client with persistence overridden by the in-memory unit of work."""
    unit_of_work = MockUnitOfWork(
        pending_commands=pending_command_repository,
        expense_entries=expense_entry_repository,
    )
    app = create_app()
    container: Container = app.state.container
    # dependency_injector's stubs leave Provider.override partially generic.
    container.unit_of_work.override(  # pyright: ignore[reportUnknownMemberType]
        unit_of_work
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
        "Record expense of 23.7 EUR at Mercator, paid by mem-1"
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


def test_approve_command_endpoint_should_execute_and_approve_when_command_pending(
    client: TestClient, expense_entry_repository: MockExpenseEntryRepository
) -> None:
    response = client.post(
        "/approve_command", json={"command_id": "cmd-1", "member_id": "mem-2"}
    )

    assert response.status_code == 200
    command = response.json()["command"]
    assert command["status"] == "approved"
    assert command["decided_by"] == "mem-2"
    assert command["decided_at"] is not None
    assert [entry.amount for entry in expense_entry_repository.entries] == [23.70]


def test_approve_command_endpoint_should_return_409_when_command_already_decided(
    client: TestClient, expense_entry_repository: MockExpenseEntryRepository
) -> None:
    first = client.post(
        "/approve_command", json={"command_id": "cmd-1", "member_id": "mem-1"}
    )
    second = client.post(
        "/approve_command", json={"command_id": "cmd-1", "member_id": "mem-2"}
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert "not pending" in second.json()["detail"]
    assert len(expense_entry_repository.entries) == 1


def test_approve_command_endpoint_should_return_409_with_reason_when_split_invalid(
    client: TestClient,
    pending_command_repository: MockPendingCommandRepository,
    expense_entry_repository: MockExpenseEntryRepository,
) -> None:
    stale = pending_command_repository.commands[0]
    pending_command_repository.commands[0] = PendingCommand(
        id=stale.id,
        household_id=stale.household_id,
        capture_id=stale.capture_id,
        verb=stale.verb,
        payload={**stale.payload, "split": {"mem-1": 5.00}},
        provenance=stale.provenance,
        status=stale.status,
        created_at=stale.created_at,
    )

    response = client.post(
        "/approve_command", json={"command_id": "cmd-1", "member_id": "mem-1"}
    )

    assert response.status_code == 409
    assert "split" in response.json()["detail"]
    assert expense_entry_repository.entries == []


def test_approve_command_endpoint_should_return_404_when_command_unknown(
    client: TestClient,
) -> None:
    response = client.post(
        "/approve_command", json={"command_id": "missing", "member_id": "mem-1"}
    )

    assert response.status_code == 404


def test_reject_command_endpoint_should_mark_rejected_and_execute_nothing(
    client: TestClient, expense_entry_repository: MockExpenseEntryRepository
) -> None:
    response = client.post(
        "/reject_command", json={"command_id": "cmd-1", "member_id": "mem-2"}
    )

    assert response.status_code == 200
    command = response.json()["command"]
    assert command["status"] == "rejected"
    assert command["decided_by"] == "mem-2"
    assert expense_entry_repository.entries == []


def test_reject_command_endpoint_should_return_409_when_command_already_decided(
    client: TestClient,
) -> None:
    client.post("/reject_command", json={"command_id": "cmd-1", "member_id": "mem-1"})

    response = client.post(
        "/reject_command", json={"command_id": "cmd-1", "member_id": "mem-2"}
    )

    assert response.status_code == 409

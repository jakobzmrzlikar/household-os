"""Unit tests for the reject_command use case."""

from datetime import UTC, datetime

import pytest

from app.adapter.output.mock_expense_entry_repository import (
    MockExpenseEntryRepository,
)
from app.adapter.output.mock_pantry_item_repository import MockPantryItemRepository
from app.adapter.output.mock_pending_command_repository import (
    MockPendingCommandRepository,
)
from app.adapter.output.mock_unit_of_work import MockUnitOfWork
from app.application.approve_command import CommandNotFoundError
from app.application.reject_command import RejectCommandRequest, RejectCommandUsecase
from app.domain.models.pending_command import (
    CommandNotPendingError,
    CommandVerb,
    PendingCommand,
    PendingCommandStatus,
    Provenance,
)


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
def unit_of_work(
    pending_command_repository: MockPendingCommandRepository,
) -> MockUnitOfWork:
    """Mock unit of work exposing the in-memory repositories."""
    return MockUnitOfWork(pending_commands=pending_command_repository)


@pytest.fixture
def usecase(unit_of_work: MockUnitOfWork) -> RejectCommandUsecase:
    """Use case under test, handing out the mock unit of work."""
    return RejectCommandUsecase(unit_of_work_factory=lambda: unit_of_work)


async def test_reject_command_should_execute_nothing_when_command_rejected(
    usecase: RejectCommandUsecase,
    pending_command_repository: MockPendingCommandRepository,
    unit_of_work: MockUnitOfWork,
) -> None:
    rejected = await usecase(
        RejectCommandRequest(command_id="cmd-1", member_id="mem-2")
    )

    assert rejected.status is PendingCommandStatus.REJECTED
    assert rejected.decided_by == "mem-2"
    assert rejected.decided_at is not None
    assert await pending_command_repository.list_pending("hh-1") == []
    # Nothing executed: no expense entry, no pantry item.
    assert isinstance(unit_of_work.expense_entries, MockExpenseEntryRepository)
    assert unit_of_work.expense_entries.entries == []
    assert isinstance(unit_of_work.pantry_items, MockPantryItemRepository)
    assert unit_of_work.pantry_items.items == {}


async def test_reject_command_should_fail_closed_when_command_already_rejected(
    usecase: RejectCommandUsecase,
    pending_command_repository: MockPendingCommandRepository,
) -> None:
    await usecase(RejectCommandRequest(command_id="cmd-1", member_id="mem-1"))

    with pytest.raises(CommandNotPendingError):
        await usecase(RejectCommandRequest(command_id="cmd-1", member_id="mem-2"))

    command = await pending_command_repository.get("cmd-1")
    assert command is not None
    assert command.decided_by == "mem-1"


async def test_reject_command_should_raise_error_when_command_unknown(
    usecase: RejectCommandUsecase,
) -> None:
    with pytest.raises(CommandNotFoundError):
        await usecase(RejectCommandRequest(command_id="missing", member_id="mem-1"))


def test_reject_command_request_should_raise_error_when_command_id_blank() -> None:
    with pytest.raises(ValueError, match="command_id"):
        RejectCommandRequest(command_id="  ", member_id="mem-1")

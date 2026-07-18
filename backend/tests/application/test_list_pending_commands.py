"""Unit tests for the list_pending_commands use case."""

from datetime import UTC, datetime

import pytest

from app.adapter.output.mock_pending_command_repository import (
    MockPendingCommandRepository,
)
from app.application.list_pending_commands import (
    ListPendingCommandsRequest,
    ListPendingCommandsUsecase,
)
from app.domain.models.pending_command import (
    CommandVerb,
    PendingCommand,
    PendingCommandStatus,
    Provenance,
)


@pytest.fixture
def pending_command_repository() -> MockPendingCommandRepository:
    """Mock repository recording staged commands in memory."""
    return MockPendingCommandRepository()


@pytest.fixture
def usecase(
    pending_command_repository: MockPendingCommandRepository,
) -> ListPendingCommandsUsecase:
    """Use case under test, wired to the in-memory mock."""
    return ListPendingCommandsUsecase(
        pending_command_repository=pending_command_repository
    )


def _command(
    command_id: str,
    household_id: str = "hh-1",
    status: PendingCommandStatus = PendingCommandStatus.PENDING,
) -> PendingCommand:
    return PendingCommand(
        id=command_id,
        household_id=household_id,
        capture_id="cap-1",
        verb=CommandVerb.ADJUST_PANTRY_ITEM,
        payload={"name": "Milk", "quantity": 2, "unit": "l"},
        provenance=Provenance(agent_name="mock_extraction_agent", model_id="mock"),
        status=status,
        created_at=datetime.now(UTC),
    )


async def test_list_pending_commands_should_return_only_pending_when_statuses_mixed(
    usecase: ListPendingCommandsUsecase,
    pending_command_repository: MockPendingCommandRepository,
) -> None:
    pending = _command("cmd-1")
    await pending_command_repository.add(pending)
    await pending_command_repository.add(
        _command("cmd-2", status=PendingCommandStatus.APPROVED)
    )

    commands = await usecase(ListPendingCommandsRequest(household_id="hh-1"))

    assert commands == [pending]


async def test_list_pending_commands_should_scope_to_household_when_others_exist(
    usecase: ListPendingCommandsUsecase,
    pending_command_repository: MockPendingCommandRepository,
) -> None:
    mine = _command("cmd-1")
    await pending_command_repository.add(mine)
    await pending_command_repository.add(_command("cmd-2", household_id="hh-2"))

    commands = await usecase(ListPendingCommandsRequest(household_id="hh-1"))

    assert commands == [mine]


def test_list_pending_commands_request_should_raise_error_when_household_id_blank() -> (
    None
):
    with pytest.raises(ValueError, match="household_id"):
        ListPendingCommandsRequest(household_id="  ")

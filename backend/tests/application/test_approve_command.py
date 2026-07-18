"""Unit tests for the approve_command use case."""

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
from app.application.approve_command import (
    ApproveCommandRequest,
    ApproveCommandUsecase,
    CommandNotFoundError,
)
from app.application.execute_verb import InvalidCommandError
from app.domain.models.pantry_item import PantryItem
from app.domain.models.pending_command import (
    CommandNotPendingError,
    CommandVerb,
    PendingCommand,
    PendingCommandStatus,
    Provenance,
)

EXPENSE_PAYLOAD: dict[str, object] = {
    "amount": 23.70,
    "currency": "EUR",
    "merchant": "Mercator",
    "payer_member_id": "mem-1",
    "split": {"mem-1": 11.85, "mem-2": 11.85},
}


@pytest.fixture
def pending_command_repository() -> MockPendingCommandRepository:
    """Mock repository recording staged commands in memory."""
    return MockPendingCommandRepository()


@pytest.fixture
def pantry_item_repository() -> MockPantryItemRepository:
    """Mock repository recording pantry items in memory."""
    return MockPantryItemRepository()


@pytest.fixture
def expense_entry_repository() -> MockExpenseEntryRepository:
    """Mock repository recording expense entries in memory."""
    return MockExpenseEntryRepository()


@pytest.fixture
def unit_of_work(
    pending_command_repository: MockPendingCommandRepository,
    pantry_item_repository: MockPantryItemRepository,
    expense_entry_repository: MockExpenseEntryRepository,
) -> MockUnitOfWork:
    """Mock unit of work exposing the in-memory repositories."""
    return MockUnitOfWork(
        pending_commands=pending_command_repository,
        pantry_items=pantry_item_repository,
        expense_entries=expense_entry_repository,
    )


@pytest.fixture
def usecase(unit_of_work: MockUnitOfWork) -> ApproveCommandUsecase:
    """Use case under test, handing out the mock unit of work."""
    return ApproveCommandUsecase(unit_of_work_factory=lambda: unit_of_work)


def _command(verb: CommandVerb, payload: dict[str, object]) -> PendingCommand:
    return PendingCommand(
        id="cmd-1",
        household_id="hh-1",
        capture_id="cap-1",
        verb=verb,
        payload=payload,
        provenance=Provenance(agent_name="mock_extraction_agent", model_id="mock"),
        status=PendingCommandStatus.PENDING,
        created_at=datetime.now(UTC),
    )


async def test_approve_command_should_record_expense_when_expense_command_pending(
    usecase: ApproveCommandUsecase,
    pending_command_repository: MockPendingCommandRepository,
    expense_entry_repository: MockExpenseEntryRepository,
) -> None:
    await pending_command_repository.add(
        _command(CommandVerb.RECORD_EXPENSE, EXPENSE_PAYLOAD)
    )

    approved = await usecase(
        ApproveCommandRequest(command_id="cmd-1", member_id="mem-2")
    )

    assert approved.status is PendingCommandStatus.APPROVED
    assert approved.decided_by == "mem-2"
    assert approved.decided_at is not None
    (entry,) = expense_entry_repository.entries
    assert entry.household_id == "hh-1"
    assert entry.amount == 23.70
    assert entry.split == {"mem-1": 11.85, "mem-2": 11.85}
    assert await pending_command_repository.list_pending("hh-1") == []


async def test_approve_command_should_execute_exactly_once_when_approved_twice(
    usecase: ApproveCommandUsecase,
    pending_command_repository: MockPendingCommandRepository,
    expense_entry_repository: MockExpenseEntryRepository,
) -> None:
    await pending_command_repository.add(
        _command(CommandVerb.RECORD_EXPENSE, EXPENSE_PAYLOAD)
    )
    await usecase(ApproveCommandRequest(command_id="cmd-1", member_id="mem-1"))

    with pytest.raises(CommandNotPendingError):
        await usecase(ApproveCommandRequest(command_id="cmd-1", member_id="mem-2"))

    assert len(expense_entry_repository.entries) == 1


async def test_approve_command_should_fail_closed_when_split_does_not_sum_to_amount(
    usecase: ApproveCommandUsecase,
    pending_command_repository: MockPendingCommandRepository,
    expense_entry_repository: MockExpenseEntryRepository,
    unit_of_work: MockUnitOfWork,
) -> None:
    payload: dict[str, object] = {**EXPENSE_PAYLOAD, "split": {"mem-1": 5.00}}
    await pending_command_repository.add(_command(CommandVerb.RECORD_EXPENSE, payload))

    with pytest.raises(InvalidCommandError, match="split"):
        await usecase(ApproveCommandRequest(command_id="cmd-1", member_id="mem-1"))

    # Fail closed: nothing executed, the command is still pending, and the
    # transaction was rolled back.
    assert expense_entry_repository.entries == []
    still_pending = await pending_command_repository.list_pending("hh-1")
    assert [command.id for command in still_pending] == ["cmd-1"]
    assert unit_of_work.rollbacks == 1
    assert unit_of_work.commits == 0


async def test_approve_command_should_create_pantry_item_when_item_new(
    usecase: ApproveCommandUsecase,
    pending_command_repository: MockPendingCommandRepository,
    pantry_item_repository: MockPantryItemRepository,
) -> None:
    await pending_command_repository.add(
        _command(
            CommandVerb.ADJUST_PANTRY_ITEM,
            {"name": "Milk", "quantity": 2.0, "unit": "l"},
        )
    )

    await usecase(ApproveCommandRequest(command_id="cmd-1", member_id="mem-1"))

    item = await pantry_item_repository.get("hh-1", "Milk")
    assert item is not None
    assert item.quantity == 2.0
    assert item.unit == "l"


async def test_approve_command_should_add_delta_when_item_exists(
    usecase: ApproveCommandUsecase,
    pending_command_repository: MockPendingCommandRepository,
    pantry_item_repository: MockPantryItemRepository,
) -> None:
    await pantry_item_repository.upsert(
        PantryItem(
            id="item-1",
            household_id="hh-1",
            name="Milk",
            quantity=2.0,
            unit="l",
            restock_threshold=1.0,
        )
    )
    await pending_command_repository.add(
        _command(
            CommandVerb.ADJUST_PANTRY_ITEM,
            {"name": "Milk", "quantity": 1.5, "unit": "l"},
        )
    )

    await usecase(ApproveCommandRequest(command_id="cmd-1", member_id="mem-1"))

    item = await pantry_item_repository.get("hh-1", "Milk")
    assert item is not None
    assert item.id == "item-1"
    assert item.quantity == 3.5
    assert item.restock_threshold == 1.0


async def test_approve_command_should_zero_stock_when_out_of_stock_approved(
    usecase: ApproveCommandUsecase,
    pending_command_repository: MockPendingCommandRepository,
    pantry_item_repository: MockPantryItemRepository,
) -> None:
    await pantry_item_repository.upsert(
        PantryItem(
            id="item-1",
            household_id="hh-1",
            name="Milk",
            quantity=2.0,
            unit="l",
            restock_threshold=1.0,
        )
    )
    await pending_command_repository.add(
        _command(
            CommandVerb.ADJUST_PANTRY_ITEM,
            {"name": "Milk", "out_of_stock": True, "note": "finished this morning"},
        )
    )

    await usecase(ApproveCommandRequest(command_id="cmd-1", member_id="mem-1"))

    item = await pantry_item_repository.get("hh-1", "Milk")
    assert item is not None
    assert item.quantity == 0.0
    # The voice-staged payload carries no unit; the existing one is preserved.
    assert item.unit == "l"


async def test_approve_command_should_create_depleted_item_when_out_of_stock_item_new(
    usecase: ApproveCommandUsecase,
    pending_command_repository: MockPendingCommandRepository,
    pantry_item_repository: MockPantryItemRepository,
) -> None:
    await pending_command_repository.add(
        _command(
            CommandVerb.ADJUST_PANTRY_ITEM,
            {"name": "Olive oil", "out_of_stock": True},
        )
    )

    await usecase(ApproveCommandRequest(command_id="cmd-1", member_id="mem-1"))

    item = await pantry_item_repository.get("hh-1", "Olive oil")
    assert item is not None
    assert item.quantity == 0.0
    assert item.unit == "pcs"


async def test_approve_command_should_preserve_unit_when_voice_delta_has_none(
    usecase: ApproveCommandUsecase,
    pending_command_repository: MockPendingCommandRepository,
    pantry_item_repository: MockPantryItemRepository,
) -> None:
    await pantry_item_repository.upsert(
        PantryItem(
            id="item-1", household_id="hh-1", name="Milk", quantity=2.0, unit="l"
        )
    )
    await pending_command_repository.add(
        _command(CommandVerb.ADJUST_PANTRY_ITEM, {"name": "Milk", "quantity": -1.0})
    )

    await usecase(ApproveCommandRequest(command_id="cmd-1", member_id="mem-1"))

    item = await pantry_item_repository.get("hh-1", "Milk")
    assert item is not None
    assert item.quantity == 1.0
    assert item.unit == "l"


async def test_approve_command_should_fail_closed_when_delta_drives_stock_negative(
    usecase: ApproveCommandUsecase,
    pending_command_repository: MockPendingCommandRepository,
    pantry_item_repository: MockPantryItemRepository,
) -> None:
    await pantry_item_repository.upsert(
        PantryItem(
            id="item-1", household_id="hh-1", name="Milk", quantity=1.0, unit="l"
        )
    )
    await pending_command_repository.add(
        _command(
            CommandVerb.ADJUST_PANTRY_ITEM,
            {"name": "Milk", "quantity": -5.0, "unit": "l"},
        )
    )

    with pytest.raises(InvalidCommandError, match="quantity"):
        await usecase(ApproveCommandRequest(command_id="cmd-1", member_id="mem-1"))

    item = await pantry_item_repository.get("hh-1", "Milk")
    assert item is not None
    assert item.quantity == 1.0
    still_pending = await pending_command_repository.list_pending("hh-1")
    assert [command.id for command in still_pending] == ["cmd-1"]


async def test_approve_command_should_fail_closed_when_payload_smuggles_household(
    usecase: ApproveCommandUsecase,
    pending_command_repository: MockPendingCommandRepository,
    expense_entry_repository: MockExpenseEntryRepository,
) -> None:
    payload: dict[str, object] = {**EXPENSE_PAYLOAD, "household_id": "hh-2"}
    await pending_command_repository.add(_command(CommandVerb.RECORD_EXPENSE, payload))

    with pytest.raises(InvalidCommandError):
        await usecase(ApproveCommandRequest(command_id="cmd-1", member_id="mem-1"))

    assert expense_entry_repository.entries == []


async def test_approve_command_should_raise_error_when_command_unknown(
    usecase: ApproveCommandUsecase,
) -> None:
    with pytest.raises(CommandNotFoundError):
        await usecase(ApproveCommandRequest(command_id="missing", member_id="mem-1"))


def test_approve_command_request_should_raise_error_when_member_id_blank() -> None:
    with pytest.raises(ValueError, match="member_id"):
        ApproveCommandRequest(command_id="cmd-1", member_id="   ")

"""Executable verbs: revalidate a staged command's payload and apply it.

Only the approval flow calls into this module — agent-staged commands stay
inert until a member approves them. Payloads are re-parsed with pydantic even
though they were validated at staging time: they cross back in from
persistence, and household state may have moved since they were staged.
"""

from datetime import UTC, datetime
from uuid import uuid4

from attrs import evolve
from pydantic import BaseModel, ConfigDict, ValidationError

from app.domain.models.expense_entry import ExpenseEntry
from app.domain.models.pantry_item import PantryItem
from app.domain.models.pending_command import CommandVerb, PendingCommand
from app.domain.ports.unit_of_work import UnitOfWorkPort


class InvalidCommandError(ValueError):
    """Raised when a command's payload fails revalidation against current state."""


class RecordExpensePayload(BaseModel):
    """Arguments of the record_expense verb.

    ``extra="forbid"`` rejects any household reference smuggled into the
    payload: the executed verb takes its household scope from the command row
    alone, so a staged payload can never write across households.
    """

    model_config = ConfigDict(extra="forbid")

    amount: float
    currency: str
    merchant: str
    payer_member_id: str
    split: dict[str, float]


class AdjustPantryItemPayload(BaseModel):
    """Arguments of the adjust_pantry_item verb.

    ``quantity`` is a signed delta applied to the household's current stock of
    ``name`` (negative for consumption). ``extra="forbid"`` for the same
    cross-household reason as :class:`RecordExpensePayload`.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    quantity: float
    unit: str
    restock_threshold: float = 0.0


async def execute_verb(command: PendingCommand, unit_of_work: UnitOfWorkPort) -> None:
    """Revalidate and execute the verb a pending command proposes.

    :param command: The command whose payload to revalidate and apply.
    :param unit_of_work: Open transactional scope the writes go through.
    :raises InvalidCommandError: When the payload is malformed or violates a
        domain invariant against current state; nothing is written.
    """
    if command.verb is CommandVerb.RECORD_EXPENSE:
        await _record_expense(command, unit_of_work)
    else:
        await _adjust_pantry_item(command, unit_of_work)


async def _record_expense(
    command: PendingCommand, unit_of_work: UnitOfWorkPort
) -> None:
    """Execute record_expense: persist a new expense entry.

    :param command: The record_expense command to apply.
    :param unit_of_work: Open transactional scope the write goes through.
    :raises InvalidCommandError: When the payload is malformed, the amount is
        not positive, or the split does not sum to the amount.
    """
    payload = _parse_payload(RecordExpensePayload, command.payload)
    try:
        entry = ExpenseEntry(
            id=uuid4().hex,
            household_id=command.household_id,
            payer_member_id=payload.payer_member_id,
            merchant=payload.merchant,
            amount=payload.amount,
            currency=payload.currency,
            split=payload.split,
            created_at=datetime.now(UTC),
        )
    except ValueError as error:
        raise InvalidCommandError(str(error)) from error
    await unit_of_work.expense_entries.add(entry)


async def _adjust_pantry_item(
    command: PendingCommand, unit_of_work: UnitOfWorkPort
) -> None:
    """Execute adjust_pantry_item: upsert the household's item by name.

    :param command: The adjust_pantry_item command to apply.
    :param unit_of_work: Open transactional scope the write goes through.
    :raises InvalidCommandError: When the payload is malformed or the delta
        would drive the current quantity below zero.
    """
    payload = _parse_payload(AdjustPantryItemPayload, command.payload)
    existing = await unit_of_work.pantry_items.get(command.household_id, payload.name)
    try:
        if existing is None:
            item = PantryItem(
                id=uuid4().hex,
                household_id=command.household_id,
                name=payload.name,
                quantity=payload.quantity,
                unit=payload.unit,
                restock_threshold=payload.restock_threshold,
            )
        else:
            # evolve re-runs the entity validators, so a delta pushing the
            # stock below zero fails here, against current state.
            item = evolve(
                existing,
                quantity=existing.quantity + payload.quantity,
                unit=payload.unit,
            )
    except ValueError as error:
        raise InvalidCommandError(str(error)) from error
    await unit_of_work.pantry_items.upsert(item)


def _parse_payload[PayloadT: BaseModel](
    payload_model: type[PayloadT], payload: dict[str, object]
) -> PayloadT:
    """Parse a staged payload into its typed verb arguments.

    :param payload_model: The pydantic model describing the verb's arguments.
    :param payload: The JSON payload the command was staged with.
    :return: The validated arguments.
    :raises InvalidCommandError: When the payload does not match the model.
    """
    try:
        return payload_model.model_validate(payload)
    except ValidationError as error:
        raise InvalidCommandError(str(error)) from error

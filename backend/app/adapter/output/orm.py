"""SQLAlchemy ORM records: the relational shape of domain entities."""

from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base shared by all ORM records."""


class CaptureRecord(Base):
    """Relational record for a Capture entity."""

    __tablename__ = "captures"

    id: Mapped[str] = mapped_column(primary_key=True)
    household_id: Mapped[str] = mapped_column(index=True)
    member_id: Mapped[str]
    kind: Mapped[str]
    media_path: Mapped[str]
    created_at: Mapped[datetime]


class PendingCommandRecord(Base):
    """Relational record for a PendingCommand entity."""

    __tablename__ = "pending_commands"

    id: Mapped[str] = mapped_column(primary_key=True)
    household_id: Mapped[str] = mapped_column(index=True)
    capture_id: Mapped[str]
    verb: Mapped[str]
    # JSON-encoded verb arguments; parsed back into a dict at the repository.
    payload: Mapped[str]
    agent_name: Mapped[str]
    model_id: Mapped[str]
    transcript: Mapped[str | None]
    status: Mapped[str] = mapped_column(index=True)
    created_at: Mapped[datetime]
    decided_by: Mapped[str | None]
    decided_at: Mapped[datetime | None]


class PantryItemRecord(Base):
    """Relational record for a PantryItem entity."""

    __tablename__ = "pantry_items"
    __table_args__ = (UniqueConstraint("household_id", "name"),)

    id: Mapped[str] = mapped_column(primary_key=True)
    household_id: Mapped[str] = mapped_column(index=True)
    name: Mapped[str]
    quantity: Mapped[float]
    unit: Mapped[str]
    restock_threshold: Mapped[float]


class ExpenseEntryRecord(Base):
    """Relational record for an ExpenseEntry entity."""

    __tablename__ = "expense_entries"

    id: Mapped[str] = mapped_column(primary_key=True)
    household_id: Mapped[str] = mapped_column(index=True)
    payer_member_id: Mapped[str]
    merchant: Mapped[str]
    amount: Mapped[float]
    currency: Mapped[str]
    # JSON-encoded member-id -> share mapping; parsed back at the repository.
    split: Mapped[str]
    created_at: Mapped[datetime]

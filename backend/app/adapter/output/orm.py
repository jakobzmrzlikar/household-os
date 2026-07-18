"""SQLAlchemy ORM records: the relational shape of domain entities."""

from datetime import datetime

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
    status: Mapped[str] = mapped_column(index=True)
    created_at: Mapped[datetime]

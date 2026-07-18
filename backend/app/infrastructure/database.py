"""Async database engine, session factory, and schema bootstrap."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.adapter.output.orm import Base


def create_engine(database_url: str) -> AsyncEngine:
    """Create the async engine for the configured database.

    :param database_url: SQLAlchemy async database URL.
    :return: A lazily connecting async engine.
    """
    return create_async_engine(database_url)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create the session factory bound to the given engine.

    :param engine: The engine sessions will use.
    :return: A factory producing async sessions.
    """
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_schema(engine: AsyncEngine) -> None:
    """Create all ORM tables that do not exist yet.

    Startup stopgap until Alembic is initialized (see CLAUDE.md); replace with
    ``alembic upgrade head`` once migrations exist.

    :param engine: The engine to run DDL against.
    """
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

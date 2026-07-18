"""Application settings parsed from the environment and the backend .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the backend service.

    :param database_url: SQLAlchemy async database URL.
    :param uploads_dir: Directory where uploaded media files are stored.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./household.db"
    uploads_dir: Path = Path("uploads")

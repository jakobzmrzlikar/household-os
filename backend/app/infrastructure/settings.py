"""Application settings parsed from the environment and the backend .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the backend service.

    :param database_url: SQLAlchemy async database URL.
    :param uploads_dir: Directory where uploaded media files are stored.
    :param extraction_model: Pydantic AI model identifier the receipt
        extraction agent runs on (``provider:model`` form).
    :param openai_api_key: API key for the OpenAI provider. Read from the
        backend ``.env`` file here because provider SDKs only look at the
        process environment, which plain ``uvicorn`` does not populate
        from ``.env``.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./household.db"
    uploads_dir: Path = Path("uploads")
    extraction_model: str = "openai:gpt-5-mini"
    openai_api_key: str | None = None

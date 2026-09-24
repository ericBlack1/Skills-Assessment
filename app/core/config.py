from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables or a .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Task Manager API"
    app_version: str = "0.1.0"
    debug: bool = False

    database_url: str

    @field_validator("database_url")
    @classmethod
    def require_psycopg_driver(cls, value: str) -> str:
        """Pin the URL to psycopg 3.

        Managed providers hand out `postgresql://` (or `postgres://`) URLs, but
        SQLAlchemy maps those to psycopg2, which this project does not install.
        """
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                return f"postgresql+psycopg://{value[len(prefix):]}"
        return value


settings = Settings()

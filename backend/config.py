from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    # Environment variables override values from backend/.env.
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    db_driver: str = "postgresql+psycopg2"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "techrep"
    db_user: str = "techrep"
    db_password: SecretStr
    # Full connection URL; when set it replaces the DB_* values above.
    database_url: str | None = None
    db_echo: bool = False

    solver_max_seconds: float = 10.0

    @property
    def sqlalchemy_url(self) -> URL | str:
        if self.database_url:
            return self.database_url
        return URL.create(
            self.db_driver,
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


settings = Settings()

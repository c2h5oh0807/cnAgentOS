from functools import lru_cache

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_name: str = "cnAgentOS"
    environment: str = Field(default="development", validation_alias="APP_ENV")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/cnagentos.db",
        validation_alias=AliasChoices("DATABASE_URL", "CNAGENTOS_DATABASE_URL"),
    )
    csrf_secret: str = Field(
        default="development-only-change-me",
        validation_alias="CSRF_SECRET",
        min_length=16,
    )
    encryption_key: str = Field(
        default="dev-only-32-byte-key-for-testing",
        validation_alias="ENCRYPTION_KEY",
        min_length=32,
    )
    session_hours: int = Field(
        default=8, validation_alias="SESSION_HOURS", gt=0, le=720
    )
    cookie_secure: bool = Field(default=False, validation_alias="COOKIE_SECURE")

    # --- Multi-database support (Phase 5) ---
    active_database: str = Field(
        default="sqlite",
        validation_alias=AliasChoices("ACTIVE_DATABASE", "CNAGENTOS_ACTIVE_DATABASE"),
    )
    mysql_host: str = Field(default="127.0.0.1", validation_alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, validation_alias="MYSQL_PORT", ge=1, le=65535)
    mysql_user: str = Field(default="cnagentos", validation_alias="MYSQL_USER")
    mysql_password: str = Field(default="cnagentos_pass_here", validation_alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="cnagentos", validation_alias="MYSQL_DATABASE")

    @property
    def session_cookie_name(self) -> str:
        if self.environment.lower() == "production":
            return "__Host-cnagentos_session"
        return "cnagentos_session"

    @property
    def use_secure_cookie(self) -> bool:
        return self.environment.lower() == "production" or self.cookie_secure

    @property
    def sync_database_url(self) -> str:
        """Return a sync database URL for APScheduler's SQLAlchemyJobStore."""
        url = self.database_url
        for prefix in ("+aiosqlite", "+asyncpg", "+asyncmy", "+aiomysql"):
            url = url.replace(prefix, "")
        return url

    @property
    def resolved_database_url(self) -> str:
        """Return the database URL based on active_database setting.

        When active_database is 'mysql', constructs a MySQL connection URL
        from the MYSQL_* fields. Otherwise returns database_url (SQLite).
        """
        if self.active_database == "mysql":
            return (
                f"mysql+asyncmy://{self.mysql_user}:{self.mysql_password}"
                f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            )
        return self.database_url

    @model_validator(mode="after")
    def production_must_set_secrets(self):
        if self.environment.lower() == "production":
            if self.csrf_secret == "development-only-change-me":
                raise ValueError("production requires an explicit CSRF_SECRET")
            if self.encryption_key == "dev-only-32-byte-key-for-testing":
                raise ValueError("production requires an explicit ENCRYPTION_KEY")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

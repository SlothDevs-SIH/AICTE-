from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/samanvay.db"
    secret_key: str  # required, no default
    pii_encryption_key: str  # required, no default
    environment: str = "dev"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    max_upload_mb: int = 10
    log_level: str = "INFO"
    phase: str = "B1"
    version: str = "0.1.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

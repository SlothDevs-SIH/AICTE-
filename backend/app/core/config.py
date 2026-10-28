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


def _load_env_file() -> None:
    """Make values in backend/.env visible to code that reads os.environ (model key, mail key). Real env wins."""
    import os
    from pathlib import Path

    f = Path(__file__).resolve().parents[2] / ".env"
    if not f.is_file():
        return
    for line in f.read_text(encoding="utf8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        if v:
            os.environ.setdefault(k.strip(), v)


_load_env_file()


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

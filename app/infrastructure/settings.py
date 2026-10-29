from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    extraction_service_url: str = "http://localhost:8001"
    storage_service_url: str = "http://localhost:8002"
    max_pdf_size_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    upstream_timeout_seconds: float = Field(default=30, gt=0)
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()

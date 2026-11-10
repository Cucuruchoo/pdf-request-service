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
    max_concurrent_pdf_uploads: int = Field(default=4, ge=1)
    circuit_failure_threshold: int = Field(default=3, ge=1)
    circuit_recovery_seconds: float = Field(default=15, gt=0)
    upstream_retry_attempts: int = Field(default=2, ge=0, le=5)
    upstream_retry_base_delay_seconds: float = Field(default=0.1, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()

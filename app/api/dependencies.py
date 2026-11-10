from collections.abc import AsyncIterator

import httpx

from app.application.request_service import RequestService
from app.infrastructure.http_clients import HttpExtractionClient, HttpStorageClient
from app.infrastructure.request_logging import request_id_context
from app.infrastructure.resilience import CircuitBreaker
from app.infrastructure.settings import get_settings
from app.infrastructure.upload_limiter import PdfUploadLimiter

settings = get_settings()
# Shared across requests inside this process (not across replicas).
_extraction_breaker = CircuitBreaker(
    "extraction", settings.circuit_failure_threshold, settings.circuit_recovery_seconds
)
_storage_breaker = CircuitBreaker(
    "storage", settings.circuit_failure_threshold, settings.circuit_recovery_seconds
)


async def get_request_service() -> AsyncIterator[RequestService]:
    settings = get_settings()
    request_id = request_id_context.get()
    async with httpx.AsyncClient(
        timeout=settings.upstream_timeout_seconds,
        headers={"X-Request-ID": request_id},
    ) as client:
        yield RequestService(
            extraction=HttpExtractionClient(
                client,
                settings.extraction_service_url,
                breaker=_extraction_breaker,
                max_retries=settings.upstream_retry_attempts,
                retry_base_delay_seconds=settings.upstream_retry_base_delay_seconds,
            ),
            storage=HttpStorageClient(
                client,
                settings.storage_service_url,
                breaker=_storage_breaker,
                max_retries=settings.upstream_retry_attempts,
                retry_base_delay_seconds=settings.upstream_retry_base_delay_seconds,
            ),
            max_pdf_size_bytes=settings.max_pdf_size_bytes,
        )


_upload_limiter = PdfUploadLimiter(settings.max_concurrent_pdf_uploads)


def get_upload_limiter() -> PdfUploadLimiter:
    return _upload_limiter

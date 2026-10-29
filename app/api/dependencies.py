
from collections.abc import AsyncIterator

import httpx

from app.application.request_service import RequestService
from app.infrastructure.http_clients import (
    HttpExtractionClient,
    HttpStorageClient,
)
from app.infrastructure.request_logging import request_id_context
from app.infrastructure.settings import get_settings


async def get_request_service() -> AsyncIterator[RequestService]:
    settings = get_settings()

    # Identificador generado por el middleware
    request_id = request_id_context.get()

    # Propagar el identificador a los servicios internos
    async with httpx.AsyncClient(
        timeout=settings.upstream_timeout_seconds,
        headers={"X-Request-ID": request_id},
    ) as client:
        yield RequestService(
            extraction=HttpExtractionClient(
                client,
                settings.extraction_service_url,
            ),
            storage=HttpStorageClient(
                client,
                settings.storage_service_url,
            ),
            max_pdf_size_bytes=settings.max_pdf_size_bytes,
        )

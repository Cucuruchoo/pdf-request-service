
import httpx
import pytest

from app.domain.errors import UpstreamError
from app.infrastructure.http_clients import (
    HttpExtractionClient,
    HttpStorageClient,
)

PDF_CONTENT = b"%PDF-1.4\nhello"


@pytest.mark.asyncio
async def test_extraction_client_sends_raw_pdf():
    async def handle(
        request: httpx.Request,
    ) -> httpx.Response:
        assert str(request.url) == (
            "http://extract/internal/v1/extract"
        )

        assert request.method == "POST"

        assert request.headers["content-type"] == (
            "application/pdf"
        )

        assert request.headers["x-filename"] == (
            "report.pdf"
        )

        assert request.content == PDF_CONTENT

        return httpx.Response(
            200,
            json={
                "filename": "report.pdf",
                "content_text": "hello",
                "character_count": 5,
                "size_bytes": len(PDF_CONTENT),
            },
        )

    transport = httpx.MockTransport(handle)

    async with httpx.AsyncClient(
        transport=transport
    ) as client:
        extraction = HttpExtractionClient(
            client,
            "http://extract",
        )

        result = await extraction.extract(
            PDF_CONTENT,
            "report.pdf",
        )

    assert result["content_text"] == "hello"
    assert result["filename"] == "report.pdf"


@pytest.mark.asyncio
async def test_storage_duplicate_propagates_409():
    async def handle(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            409,
            json={
                "detail": "Document already exists."
            },
        )

    transport = httpx.MockTransport(handle)

    async with httpx.AsyncClient(
        transport=transport
    ) as client:
        storage = HttpStorageClient(
            client,
            "http://store",
        )

        with pytest.raises(
            UpstreamError
        ) as error:
            await storage.create({
                "checksum": "abc"
            })

    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_unexpected_storage_failure_maps_to_bad_gateway():
    async def handle(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            500,
            json={
                "detail": "Database unavailable"
            },
        )

    transport = httpx.MockTransport(handle)

    async with httpx.AsyncClient(
        transport=transport
    ) as client:
        storage = HttpStorageClient(
            client,
            "http://store",
        )

        with pytest.raises(
            UpstreamError
        ) as error:
            await storage.list_all()

    assert error.value.status_code == 502

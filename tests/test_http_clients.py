import httpx
import pytest

from app.domain.errors import UpstreamError
from app.infrastructure.http_clients import HttpExtractionClient, HttpStorageClient


@pytest.mark.asyncio
async def test_extraction_client_uses_internal_multipart_endpoint():
    async def handle(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://extract/internal/v1/extract"
        assert request.headers["content-type"].startswith("multipart/form-data")
        assert b"report.pdf" in request.content
        return httpx.Response(200, json={"content_text": "hello"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        result = await HttpExtractionClient(client, "http://extract").extract(
            b"%PDF-1.4\nhello", "report.pdf"
        )
    assert result["content_text"] == "hello"


@pytest.mark.asyncio
async def test_storage_duplicate_propagates_409():
    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"detail": "Document already exists."})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        storage = HttpStorageClient(client, "http://store")
        with pytest.raises(UpstreamError) as error:
            await storage.create({"checksum": "abc"})
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_unexpected_storage_failure_maps_to_bad_gateway():
    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "Database unavailable"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        storage = HttpStorageClient(client, "http://store")
        with pytest.raises(UpstreamError) as error:
            await storage.list_all()
    assert error.value.status_code == 502

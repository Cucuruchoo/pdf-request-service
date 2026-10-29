from datetime import UTC, datetime

import httpx
import pytest

from app.api.dependencies import get_request_service, get_upload_limiter
from app.infrastructure.upload_limiter import (
    PdfUploadLimiter,
    PdfUploadLimitError,
)
from app.main import app

PDF_CONTENT = b"%PDF-1.4\nexample\n%%EOF"


def document_fixture() -> dict:
    now = datetime.now(UTC).isoformat()
    return {
        "id": "507f1f77bcf86cd799439011",
        "filename": "report.pdf",
        "content_text": "Hello from PDF",
        "checksum": "a" * 64,
        "character_count": 14,
        "size_bytes": len(PDF_CONTENT),
        "created_at": now,
        "updated_at": now,
    }


class FakeService:
    max_pdf_size_bytes = 1024

    async def upload(self, data: bytes, filename: str) -> dict:
        assert data == PDF_CONTENT
        assert filename == "report.pdf"
        return document_fixture()

    async def list_all(self) -> list[dict]:
        return [document_fixture()]

    async def get(self, document_id: str) -> dict:
        return document_fixture()

    async def update(self, document_id: str, payload: dict) -> dict:
        result = document_fixture()
        result.update(payload)
        return result

    async def delete(self, document_id: str) -> None:
        return None


@pytest.fixture
async def client():
    app.dependency_overrides[get_request_service] = lambda: FakeService()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_pdf_upload(client):
    response = await client.post(
        "/api/v1/documents",
        content=PDF_CONTENT,
        headers={"content-type": "application/pdf", "x-filename": "report.pdf"},
    )
    assert response.status_code == 201
    assert response.json()["filename"] == "report.pdf"


@pytest.mark.asyncio
async def test_invalid_media_type_returns_415(client):
    response = await client.post(
        "/api/v1/documents",
        content=b"nope",
        headers={"content-type": "text/plain", "x-filename": "report.pdf"},
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_list_documents(client):
    response = await client.get("/api/v1/documents")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_document_update(client):
    response = await client.patch(
        "/api/v1/documents/abc", json={"filename": "changed.pdf"}
    )
    assert response.status_code == 200
    assert response.json()["filename"] == "changed.pdf"


@pytest.mark.asyncio
async def test_document_delete(client):
    response = await client.delete("/api/v1/documents/abc")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_upload_returns_429_when_at_capacity(client):
    limiter = PdfUploadLimiter(max_concurrent=1)

    app.dependency_overrides[get_upload_limiter] = (
        lambda: limiter
    )

    try:
        async with limiter.slot():
            response = await client.post(
                "/api/v1/documents",
                content=PDF_CONTENT,
                headers={
                    "content-type": "application/pdf",
                    "x-filename": "report.pdf",
                },
            )

        assert response.status_code == 429

    finally:
        app.dependency_overrides.pop(
            get_upload_limiter,
            None,
        )


@pytest.mark.asyncio
async def test_limiter_releases_slot_after_error():
    limiter = PdfUploadLimiter(max_concurrent=1)

    with pytest.raises(RuntimeError):
        async with limiter.slot():
            raise RuntimeError("Test error")

    # Debe permitir otra carga después del error.
    async with limiter.slot():
        assert limiter._active == 1


@pytest.mark.asyncio
async def test_limiter_rejects_excess_slots():
    limiter = PdfUploadLimiter(max_concurrent=2)

    async with limiter.slot(), limiter.slot():
        with pytest.raises(PdfUploadLimitError):
            async with limiter.slot():
                pass

    assert limiter._active == 0

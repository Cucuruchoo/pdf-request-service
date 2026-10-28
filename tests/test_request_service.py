import hashlib

import pytest

from app.application.request_service import RequestService
from app.domain.errors import PdfValidationError

PDF_CONTENT = b"%PDF-1.4\nexample\n%%EOF"


class FakeExtraction:
    async def extract(self, data: bytes, filename: str) -> dict:
        return {"filename": filename, "content_text": "Hello from PDF"}


class FakeStorage:
    def __init__(self):
        self.created = None

    async def create(self, payload: dict) -> dict:
        self.created = payload
        return payload


@pytest.mark.asyncio
async def test_upload_extracts_text_and_persists_sha256():
    storage = FakeStorage()
    service = RequestService(FakeExtraction(), storage, max_pdf_size_bytes=1024)

    await service.upload(PDF_CONTENT, "report.pdf")

    assert storage.created == {
        "filename": "report.pdf",
        "content_text": "Hello from PDF",
        "checksum": hashlib.sha256(PDF_CONTENT).hexdigest(),
        "size_bytes": len(PDF_CONTENT),
    }


@pytest.mark.asyncio
async def test_upload_rejects_invalid_pdf_before_calling_storage():
    storage = FakeStorage()
    service = RequestService(FakeExtraction(), storage, max_pdf_size_bytes=1024)

    with pytest.raises(PdfValidationError, match="signature"):
        await service.upload(b"NOT A PDF", "report.pdf")

    assert storage.created is None


@pytest.mark.asyncio
async def test_upload_rejects_pdf_over_limit():
    service = RequestService(FakeExtraction(), FakeStorage(), max_pdf_size_bytes=5)

    with pytest.raises(PdfValidationError, match="maximum"):
        await service.upload(PDF_CONTENT, "report.pdf")

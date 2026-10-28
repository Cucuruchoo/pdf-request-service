from typing import Protocol

from app.domain.pdf import calculate_checksum, validate_pdf


class ExtractionClient(Protocol):
    async def extract(self, data: bytes, filename: str) -> dict: ...


class StorageClient(Protocol):
    async def create(self, payload: dict) -> dict: ...
    async def list_all(self) -> list[dict]: ...
    async def get(self, document_id: str) -> dict: ...
    async def update(self, document_id: str, payload: dict) -> dict: ...
    async def delete(self, document_id: str) -> None: ...


class RequestService:
    def __init__(
        self,
        extraction: ExtractionClient,
        storage: StorageClient,
        max_pdf_size_bytes: int,
    ):
        self.extraction = extraction
        self.storage = storage
        self.max_pdf_size_bytes = max_pdf_size_bytes

    async def upload(self, data: bytes, filename: str) -> dict:
        validate_pdf(data, filename, self.max_pdf_size_bytes)
        checksum = calculate_checksum(data)
        extracted = await self.extraction.extract(data, filename)
        return await self.storage.create(
            {
                "filename": filename,
                "content_text": extracted["content_text"],
                "checksum": checksum,
                "size_bytes": len(data),
            }
        )

    async def list_all(self) -> list[dict]:
        return await self.storage.list_all()

    async def get(self, document_id: str) -> dict:
        return await self.storage.get(document_id)

    async def update(self, document_id: str, payload: dict) -> dict:
        return await self.storage.update(document_id, payload)

    async def delete(self, document_id: str) -> None:
        await self.storage.delete(document_id)

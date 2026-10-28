import httpx

from app.domain.errors import UpstreamError


def _raise_for_upstream_error(response: httpx.Response) -> None:
    if response.is_success:
        return

    status_code = response.status_code
    if status_code not in {400, 404, 409, 422}:
        status_code = 502

    try:
        detail = response.json().get("detail", "Upstream service error.")
    except (ValueError, AttributeError):
        detail = "Upstream service error."
    raise UpstreamError(str(detail), status_code=status_code)


class HttpExtractionClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str):
        self.client = client
        self.base_url = base_url.rstrip("/")

    async def extract(self, data: bytes, filename: str) -> dict:
        response = await self.client.post(
            f"{self.base_url}/internal/v1/extract",
            files={"file": (filename, data, "application/pdf")},
        )
        _raise_for_upstream_error(response)
        return response.json()


class HttpStorageClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str):
        self.client = client
        self.base_url = base_url.rstrip("/")

    def _url(self, document_id: str = "") -> str:
        return f"{self.base_url}/internal/v1/documents" + (
            f"/{document_id}" if document_id else ""
        )

    async def create(self, payload: dict) -> dict:
        response = await self.client.post(self._url(), json=payload)
        _raise_for_upstream_error(response)
        return response.json()

    async def list_all(self) -> list[dict]:
        response = await self.client.get(self._url())
        _raise_for_upstream_error(response)
        return response.json()

    async def get(self, document_id: str) -> dict:
        response = await self.client.get(self._url(document_id))
        _raise_for_upstream_error(response)
        return response.json()

    async def update(self, document_id: str, payload: dict) -> dict:
        response = await self.client.patch(self._url(document_id), json=payload)
        _raise_for_upstream_error(response)
        return response.json()

    async def delete(self, document_id: str) -> None:
        response = await self.client.delete(self._url(document_id))
        _raise_for_upstream_error(response)

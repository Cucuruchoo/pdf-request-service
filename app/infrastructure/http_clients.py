import httpx

from app.domain.errors import UpstreamError
from app.infrastructure.resilience import CircuitBreaker, ResilientHttpClient


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
    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        breaker: CircuitBreaker | None = None,
        max_retries: int = 2,
        retry_base_delay_seconds: float = 0.1,
    ):
        self.client = client
        self.base_url = base_url.rstrip("/")
        self._resilient = ResilientHttpClient(
            client, breaker or CircuitBreaker("extraction"), max_retries,
            retry_base_delay_seconds,
        )

    async def extract(self, data: bytes, filename: str) -> dict:
        response = await self._resilient.request(
            "POST",
            f"{self.base_url}/internal/v1/extract",
            retry_safe=True,  # Stateless extraction can be safely repeated.
            content=data,
            headers={"Content-Type": "application/pdf", "X-Filename": filename},
        )
        _raise_for_upstream_error(response)
        return response.json()


class HttpStorageClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        breaker: CircuitBreaker | None = None,
        max_retries: int = 2,
        retry_base_delay_seconds: float = 0.1,
    ):
        self.client = client
        self.base_url = base_url.rstrip("/")
        self._resilient = ResilientHttpClient(
            client, breaker or CircuitBreaker("storage"), max_retries,
            retry_base_delay_seconds,
        )

    def _url(self, document_id: str = "") -> str:
        return f"{self.base_url}/internal/v1/documents" + (
            f"/{document_id}" if document_id else ""
        )

    async def create(self, payload: dict) -> dict:
        response = await self._resilient.request("POST", self._url(), json=payload)
        _raise_for_upstream_error(response)
        return response.json()

    async def list_all(self) -> list[dict]:
        response = await self._resilient.request("GET", self._url(), retry_safe=True)
        _raise_for_upstream_error(response)
        return response.json()

    async def get(self, document_id: str) -> dict:
        response = await self._resilient.request(
            "GET", self._url(document_id), retry_safe=True
        )
        _raise_for_upstream_error(response)
        return response.json()

    async def update(self, document_id: str, payload: dict) -> dict:
        response = await self._resilient.request(
            "PATCH", self._url(document_id), json=payload
        )
        _raise_for_upstream_error(response)
        return response.json()

    async def delete(self, document_id: str) -> None:
        response = await self._resilient.request("DELETE", self._url(document_id))
        _raise_for_upstream_error(response)

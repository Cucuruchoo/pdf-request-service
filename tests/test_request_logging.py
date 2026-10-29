
import httpx
import pytest

from app.main import app


@pytest.mark.asyncio
async def test_generates_request_id():
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_preserves_valid_request_id():
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/health",
            headers={"X-Request-ID": "prueba-123"},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "prueba-123"


@pytest.mark.asyncio
async def test_request_id_propagates_to_internal_clients():
    from app.api.dependencies import get_request_service
    from app.infrastructure.request_logging import (
        request_id_context,
    )

    token = request_id_context.set("prueba-123")

    try:
        async for service in get_request_service():
            extraction_id = (
                service.extraction.client.headers["X-Request-ID"]
            )
            storage_id = (
                service.storage.client.headers["X-Request-ID"]
            )

            assert extraction_id == "prueba-123"
            assert storage_id == "prueba-123"

    finally:
        request_id_context.reset(token)

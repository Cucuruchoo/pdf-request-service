import httpx
import pytest

from app.infrastructure.http_clients import HttpExtractionClient, HttpStorageClient
from app.infrastructure.resilience import CircuitBreaker, CircuitOpenError


@pytest.mark.asyncio
async def test_get_retries_then_succeeds():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(503 if attempts < 3 else 200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        storage = HttpStorageClient(
            client, "http://storage", max_retries=2, retry_base_delay_seconds=0
        )
        assert await storage.list_all() == []
    assert attempts == 3


@pytest.mark.asyncio
async def test_storage_post_is_not_retried():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, json={"detail": "Unavailable"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        storage = HttpStorageClient(
            client, "http://storage", max_retries=2, retry_base_delay_seconds=0
        )
        with pytest.raises(Exception):
            await storage.create({"checksum": "abc"})
    assert attempts == 1


@pytest.mark.asyncio
async def test_extraction_retries_transient_error():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"content_text": "hello"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        extract = HttpExtractionClient(
            client, "http://extract", max_retries=1, retry_base_delay_seconds=0
        )
        assert (
            await extract.extract(b"%PDF-test", "x.pdf")
        )["content_text"] == "hello"
    assert attempts == 2


@pytest.mark.asyncio
async def test_breaker_opens_and_recovers_with_probe():
    now = [0.0]
    breaker = CircuitBreaker(
        "storage", failure_threshold=2, recovery_seconds=10, clock=lambda: now[0]
    )
    await breaker.before_request()
    await breaker.on_failure()
    await breaker.before_request()
    await breaker.on_failure()
    with pytest.raises(CircuitOpenError) as exc:
        await breaker.before_request()
    assert exc.value.status_code == 503
    now[0] = 11
    await breaker.before_request()
    with pytest.raises(CircuitOpenError):
        await breaker.before_request()
    await breaker.on_success()
    await breaker.before_request()


@pytest.mark.asyncio
async def test_http_4xx_does_not_trip_circuit():
    breaker = CircuitBreaker("storage", failure_threshold=1)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(404, json={"detail": "not found"})
        )
    ) as client:
        storage = HttpStorageClient(client, "http://storage", breaker, max_retries=0)
        for _ in range(3):
            with pytest.raises(Exception) as exc:
                await storage.get("not-found")
            assert not isinstance(exc.value, CircuitOpenError)

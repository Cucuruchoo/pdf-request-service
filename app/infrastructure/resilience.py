"""Bounded retries and per-process circuit breakers for upstream HTTP calls."""

import asyncio
import time
from collections.abc import Callable

import httpx

from app.domain.errors import UpstreamError


class CircuitOpenError(UpstreamError):
    def __init__(self, service: str):
        super().__init__(f"{service} is temporarily unavailable.", status_code=503)


class CircuitBreaker:
    """Opens on repeated transient failures; allows a single half-open probe."""

    def __init__(
        self,
        service: str,
        failure_threshold: int = 3,
        recovery_seconds: float = 15.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        if failure_threshold < 1 or recovery_seconds <= 0:
            raise ValueError("Invalid circuit breaker configuration.")
        self.service = service
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None
        self._probe_in_progress = False
        self._lock = asyncio.Lock()

    async def before_request(self) -> None:
        async with self._lock:
            if self._opened_at is None:
                return
            if (
                self._clock() - self._opened_at < self.recovery_seconds
                or self._probe_in_progress
            ):
                raise CircuitOpenError(self.service)
            self._probe_in_progress = True

    async def on_success(self) -> None:
        async with self._lock:
            self._failures = 0
            self._opened_at = None
            self._probe_in_progress = False

    async def on_failure(self) -> None:
        async with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._opened_at = self._clock()
            self._probe_in_progress = False

    async def on_cancel(self) -> None:
        async with self._lock:
            self._probe_in_progress = False


class ResilientHttpClient:
    """Retry only calls explicitly marked safe to replay (not storage writes)."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        breaker: CircuitBreaker,
        max_retries: int = 2,
        base_delay_seconds: float = 0.1,
    ):
        if max_retries < 0 or base_delay_seconds < 0:
            raise ValueError("Invalid retry configuration.")
        self.client = client
        self.breaker = breaker
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds

    async def request(
        self, method: str, url: str, *, retry_safe: bool = False, **kwargs
    ) -> httpx.Response:
        await self.breaker.before_request()
        attempts = 1 + (self.max_retries if retry_safe else 0)
        try:
            for attempt in range(attempts):
                try:
                    response = await self.client.request(method, url, **kwargs)
                except httpx.RequestError:
                    if attempt + 1 < attempts:
                        await asyncio.sleep(self.base_delay_seconds * 2**attempt)
                        continue
                    raise

                if response.status_code >= 500:
                    if attempt + 1 < attempts:
                        await asyncio.sleep(self.base_delay_seconds * 2**attempt)
                        continue
                    await self.breaker.on_failure()
                else:
                    await self.breaker.on_success()
                return response
        except httpx.RequestError:
            await self.breaker.on_failure()
            raise
        except BaseException:
            await self.breaker.on_cancel()
            raise

        raise AssertionError("Retry loop was unexpectedly exhausted.")

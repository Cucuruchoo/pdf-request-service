
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class PdfUploadLimitError(Exception):
    """Se alcanzó el máximo de PDFs simultáneos."""


class PdfUploadLimiter:
    def __init__(self, max_concurrent: int):
        if max_concurrent < 1:
            raise ValueError(
                "max_concurrent must be greater than zero"
            )

        self.max_concurrent = max_concurrent
        self._active = 0
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        async with self._lock:
            if self._active >= self.max_concurrent:
                raise PdfUploadLimitError(
                    "Too many concurrent PDF uploads."
                )

            self._active += 1

        try:
            yield
        finally:
            async with self._lock:
                self._active -= 1

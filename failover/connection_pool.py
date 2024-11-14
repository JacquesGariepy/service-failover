import asyncio
import logging

DEFAULT_MAX_SIZE = 10

logger = logging.getLogger(__name__)

class ConnectionPool:
    def __init__(self, max_size=DEFAULT_MAX_SIZE):
        self._semaphore = asyncio.Semaphore(max_size)
        self._connections = []
        logger.info(f"ConnectionPool initialized with max_size={max_size}")

    async def acquire(self):
        await self._semaphore.acquire()
        logger.debug("Connection acquired")
        # Connection logic here
        return self

    async def release(self):
        self._semaphore.release()
        logger.debug("Connection released")

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.release()

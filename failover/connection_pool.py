import asyncio

DEFAULT_MAX_SIZE = 10

class ConnectionPool:
    def __init__(self, max_size=DEFAULT_MAX_SIZE):
        self._semaphore = asyncio.Semaphore(max_size)
        self._connections = []

    async def acquire(self):
        await self._semaphore.acquire()
        # Connection logic here
        return self

    async def release(self):
        self._semaphore.release()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.release()

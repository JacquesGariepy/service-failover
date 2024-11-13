
from asyncio_throttle import Throttler

DEFAULT_RATE_LIMIT = 5
DEFAULT_RATE_LIMIT_PERIOD = 1

class RateLimiter:
    def __init__(self, rate: int = DEFAULT_RATE_LIMIT, period: float = DEFAULT_RATE_LIMIT_PERIOD):
        self.throttler = Throttler(rate, period)

    async def __aenter__(self):
        await self.throttler.acquire()

    async def __aexit__(self, exc_type, exc, tb):
        pass
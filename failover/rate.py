
from asyncio_throttle import Throttle

DEFAULT_RATE_LIMIT = 5
DEFAULT_RATE_LIMIT_PERIOD = 1

class RateLimiter:
    def __init__(self, rate: int = DEFAULT_RATE_LIMIT, per: float = DEFAULT_RATE_LIMIT_PERIOD):
        self.throttle = Throttle(rate, per)

    async def __aenter__(self):
        await self.throttle.acquire()

    async def __aexit__(self, exc_type, exc, tb):
        pass
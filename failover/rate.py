from asyncio_throttle import Throttler
import logging

DEFAULT_RATE_LIMIT = 5
DEFAULT_RATE_LIMIT_PERIOD = 1

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, rate: int = DEFAULT_RATE_LIMIT, period: float = DEFAULT_RATE_LIMIT_PERIOD):
        logger.debug(f"Initializing RateLimiter with rate={rate}, period={period}")
        self.throttler = Throttler(rate, period)

    async def __aenter__(self):
        logger.debug("Acquiring rate limiter")
        await self.throttler.acquire()

    async def __aexit__(self, exc_type, exc, tb):
        logger.debug("Releasing rate limiter")
        pass
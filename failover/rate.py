from asyncio_throttle import Throttler
import logging
import configparser

# Load configuration from config file
config = configparser.ConfigParser()
config.read('config.ini')

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, rate: int = None, period: float = None):
        rate = rate or config.getint('DEFAULT', 'RATE_LIMIT', fallback=5)
        period = period or config.getfloat('DEFAULT', 'RATE_LIMIT_PERIOD', fallback=1.0)
        logger.debug(f"Initializing RateLimiter with rate={rate}, period={period}")
        self.throttler = Throttler(rate, period)

    async def __aenter__(self):
        logger.debug("Acquiring rate limiter")
        await self.throttler.acquire()

    async def __aexit__(self, exc_type, exc, tb):
        logger.debug("Releasing rate limiter")
        pass

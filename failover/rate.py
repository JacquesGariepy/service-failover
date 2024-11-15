from asyncio_throttle import Throttler
import logging
import configparser

# Load configuration from config file
config = configparser.ConfigParser()
config.read('config.ini')

# Initialize logger
logger = logging.getLogger(__name__)

class RateLimiter:
    """
    RateLimiter class to control the rate of requests.
    Uses asyncio_throttle.Throttler to manage the rate limiting.
    """

    def __init__(self, rate: int = None, period: float = None):
        """
        Initialize the RateLimiter with a specified rate and period.
        If not provided, defaults are loaded from the configuration file.

        :param rate: Number of requests allowed per period.
        :param period: Time period in seconds for the rate limit.
        """
        rate = rate or config.getint('DEFAULT', 'RATE_LIMIT', fallback=5)
        period = period or config.getfloat('DEFAULT', 'RATE_LIMIT_PERIOD', fallback=1.0)
        logger.debug(f"Initializing RateLimiter with rate={rate}, period={period}")
        self.throttler = Throttler(rate, period)

    async def __aenter__(self):
        """
        Enter the asynchronous context manager.
        Acquires the rate limiter before making a request.
        """
        logger.debug("Acquiring rate limiter")
        await self.throttler.acquire()

    async def __aexit__(self, exc_type, exc, tb):
        """
        Exit the asynchronous context manager.
        Releases the rate limiter after making a request.
        """
        logger.debug("Releasing rate limiter")
        pass

import asyncio
import random
import logging
import requests  # Add this import
import configparser  # Add this import
from typing import Callable

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read('config.ini')

class RetryPolicy:
    def __init__(self, max_attempts: int = None, base_delay: float = None, jitter: float = None):
        self.max_attempts = max_attempts or config.getint('DEFAULT', 'MAX_ATTEMPTS', fallback=3)
        self.base_delay = base_delay or config.getfloat('DEFAULT', 'BASE_DELAY', fallback=1.0)
        self.jitter = jitter or config.getfloat('DEFAULT', 'JITTER', fallback=0.5)
        logger.info(f"RetryPolicy initialized with max_attempts={self.max_attempts}, base_delay={self.base_delay}, jitter={self.jitter}")

    async def execute_with_retry(self, func: Callable, *args, **kwargs):
        for attempt in range(self.max_attempts):
            try:
                logger.debug(f"Attempt {attempt + 1} for function {func.__name__}")
                return await func(*args, **kwargs)
            except (ConnectionError, requests.exceptions.RequestException) as e:
                delay = self.base_delay * (2 ** attempt) + random.uniform(0, self.jitter)
                logger.warning(f"Attempt {attempt + 1} failed with error: {e}. Retrying in {delay:.2f} seconds.")
                await asyncio.sleep(delay)
        logger.error("Max retry attempts reached.")
        raise Exception("Max retry attempts reached.")

import asyncio
import random
import logging
import requests  # Add this import
from typing import Callable

logger = logging.getLogger(__name__)

DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_BASE_DELAY = 1.0
DEFAULT_JITTER = 0.5

class RetryPolicy:
    def __init__(self, max_attempts: int = DEFAULT_RETRY_ATTEMPTS, base_delay: float = DEFAULT_BASE_DELAY, jitter: float = DEFAULT_JITTER):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.jitter = jitter
        logger.info(f"RetryPolicy initialized with max_attempts={max_attempts}, base_delay={base_delay}, jitter={jitter}")

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

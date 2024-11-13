import aiohttp
import asyncio
import logging  # Add this import
from typing import Dict
from .service import Service
from .rate import RateLimiter
from .connection_pool import ConnectionPool
from .cache import Cache
from .metrics import MetricsCollector

DEFAULT_TIMEOUT = 5
DEFAULT_RETRY_AFTER = 60
HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE']

logger = logging.getLogger(__name__)  # Add this line

class ExternalAPIService(Service):
    def __init__(self, api_key: str, base_url: str):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self.rate_limiter = RateLimiter()

    async def request(self, endpoint: str, method: str = 'GET', params: Dict = None, data: Dict = None) -> str:
        if method not in HTTP_METHODS:
            raise ValueError(f"Unsupported HTTP method: {method}")
        cache_key = f"{method}:{endpoint}:{str(params)}:{str(data)}"
        cached_response = self.cache.get(cache_key)
        if cached_response:
            return cached_response

        async with (await self.connection_pool.acquire()):  # P39e5
            with self.metrics.latency_histogram.labels(
                service=self.__class__.__name__,
                endpoint=endpoint
            ).time():
                url = f"{self.base_url}{endpoint}"
                headers = {'Authorization': f"Bearer {self.api_key}"}
                async with self.rate_limiter:
                    try:
                        async with aiohttp.ClientSession() as session:
                            if method == 'GET':
                                async with session.get(url, headers=headers, params=params, timeout=DEFAULT_TIMEOUT) as response:
                                    result = await self._handle_response(response, endpoint)
                            elif method == 'POST':
                                async with session.post(url, headers=headers, json=data, timeout=DEFAULT_TIMEOUT) as response:
                                    result = await self._handle_response(response, endpoint)
                            elif method == 'PUT':
                                async with session.put(url, headers=headers, json=data, timeout=DEFAULT_TIMEOUT) as response:
                                    result = await self._handle_response(response, endpoint)
                            elif method == 'DELETE':
                                async with session.delete(url, headers=headers, timeout=DEFAULT_TIMEOUT) as response:
                                    result = await self._handle_response(response, endpoint)
                            else:
                                raise ValueError(f"Unsupported HTTP method: {method}")
                        self.cache.set(cache_key, result)
                        return result
                    except asyncio.TimeoutError:
                        raise ConnectionError("Request timed out.")
                    except aiohttp.ClientError as e:
                        raise ConnectionError(f"Client error: {e}")

    async def _handle_response(self, response, endpoint):
        if response.status == 429:
            retry_after = int(response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))
            logger.warning(f"Rate limited. Retrying after {retry_after} seconds.")
            await asyncio.sleep(retry_after)
            return await self.request(endpoint)
        response.raise_for_status()
        return await response.text()

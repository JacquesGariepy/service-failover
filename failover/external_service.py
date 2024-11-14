import aiohttp
import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime
from .service import Service, HealthStatus
from .rate import RateLimiter
from .metrics import MetricsCollector
from .connection_pool import ConnectionPool
from .cache import Cache

# Constants
DEFAULT_TIMEOUT = 5  # seconds
DEFAULT_RETRY_AFTER = 60  # seconds
HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE']

# Configure logging
logger = logging.getLogger(__name__)

class ExternalAPIService(Service):
    def __init__(self, api_key: str, base_url: str):
        super().__init__(base_url)
        self.api_key = api_key
        self.rate_limiter = RateLimiter()
        self.health_history: List[HealthStatus] = []  # Keep track of health check history
        
    async def request(self, endpoint: str, method: str = 'GET', params: Dict = None, data: Dict = None) -> str:
        if method not in HTTP_METHODS:
            raise ValueError(f"Unsupported HTTP method: {method}")

        # Verify service health before making request
        health_status = await self.health_check()
        if not health_status.overall_status:
            logger.error(f"Service {self.base_url} is unhealthy: {health_status.error_message}")
            raise ConnectionError(f"Service is unhealthy: {health_status.error_message}")
            
        cache_key = f"{method}:{endpoint}:{str(params)}:{str(data)}"
        cached_response = self.cache.get(cache_key)
        if cached_response:
            return cached_response

        async with self.connection_pool:
            with self.metrics.latency_histogram.labels(
                service=self.__class__.__name__,
                endpoint=endpoint
            ).time():
                url = f"{self.base_url}{endpoint}"
                headers = {
                    'Authorization': f"Bearer {self.api_key}",
                    'User-Agent': 'ExternalAPIService/1.0'
                }
                
                async with self.rate_limiter:
                    try:
                        timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            response = await self._make_request(session, method, url, headers, params, data)
                            result = await self._handle_response(response, endpoint)
                            
                        self.cache.set(cache_key, result)
                        return result
                        
                    except asyncio.TimeoutError:
                        self.metrics.record_error("timeout", f"Request to {endpoint} timed out")
                        raise ConnectionError("Request timed out")
                    except aiohttp.ClientError as e:
                        self.metrics.record_error("client_error", str(e))
                        raise ConnectionError(f"Client error: {e}")

    async def _make_request(self, session: aiohttp.ClientSession, method: str, 
                          url: str, headers: Dict, params: Optional[Dict], 
                          data: Optional[Dict]) -> aiohttp.ClientResponse:
        if method == 'GET':
            return await session.get(url, headers=headers, params=params)
        elif method == 'POST':
            return await session.post(url, headers=headers, json=data)
        elif method == 'PUT':
            return await session.put(url, headers=headers, json=data)
        elif method == 'DELETE':
            return await session.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

    async def _handle_response(self, response: aiohttp.ClientResponse, endpoint: str) -> str:
        if response.status == 429:
            retry_after = int(response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))
            logger.warning(f"Rate limited. Retrying after {retry_after} seconds.")
            self.metrics.record_error("rate_limit", f"Rate limited on {endpoint}")
            await asyncio.sleep(retry_after)
            return await self.request(endpoint)
        
        try:
            response.raise_for_status()
            return await response.text()
        except aiohttp.ClientResponseError as e:
            self.metrics.record_error("response_error", f"{e.status}: {e.message}")
            raise

    def get_health_history(self) -> List[Dict]:
        """Return the health check history in a formatted way"""
        return [status.to_dict() for status in self.health_history[-10:]]  # Keep last 10 checks

    async def verify_service_health(self, display_results: bool = True) -> bool:
        """
        Enhanced version that maintains health history and provides detailed logging
        """
        health_status = await self.health_check()
        self.health_history.append(health_status)
        
        # Trim history if it gets too long
        if len(self.health_history) > 100:
            self.health_history = self.health_history[-100:]
        
        # Update metrics with service name
        service_name = self.__class__.__name__
        self.metrics.record_health_check(
            is_healthy=health_status.overall_status,
            service_name=service_name
        )
        
        if health_status.error_message:
            self.metrics.record_error(
                error_type="health_check",
                message=health_status.error_message,
                service_name=service_name
            )
            logger.error(f"Health check failed for {self.base_url}: {health_status.error_message}")
        
        # Record DNS and ping latencies if available
        if health_status.dns_check["duration"] > 0:
            self.metrics.record_dns_latency(
                duration=health_status.dns_check["duration"],
                service_name=service_name
            )
        
        if health_status.ping_check["duration"] > 0:
            self.metrics.record_ping_latency(
                duration=health_status.ping_check["duration"],
                service_name=service_name
            )
        
        if display_results:
            print(f"\nService: {self.base_url}")
            print(health_status)
            
        return health_status.overall_status

    def __str__(self) -> str:
        """Enhanced string representation including last health status"""
        status = self._last_health_status
        if status:
            return f"ExternalAPIService({self.base_url}) - Last Check: {status.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - Status: {'Healthy' if status.overall_status else 'Unhealthy'}"
        return f"ExternalAPIService({self.base_url}) - No health check performed yet"
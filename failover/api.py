import aiohttp
import asyncio
import logging
import configparser
from typing import Dict, Optional, List
from datetime import datetime
from .service import Service, HealthStatus
from .rate import RateLimiter
from .metrics import MetricsCollector
from .connection_pool import ConnectionPool
from .cache import Cache

# Load configuration from config file
config = configparser.ConfigParser()
config.read('config.ini')

# Constants
DEFAULT_TIMEOUT = config.getint('DEFAULT', 'DEFAULT_TIMEOUT', fallback=5)  # seconds
DEFAULT_RETRY_AFTER = config.getint('DEFAULT', 'DEFAULT_RETRY_AFTER', fallback=60)  # seconds
HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE']

# Configure logging
logger = logging.getLogger(__name__)

class APIService(Service):
    def __init__(self, api_key: str, base_url: str):
        """
        Initialize the APIService with the given API key and base URL.
        
        :param api_key: The API key for authentication.
        :param base_url: The base URL of the external API service.
        """
        super().__init__(base_url)
        self.api_key = api_key
        self.rate_limiter = RateLimiter()
        self.health_history: List[HealthStatus] = []  # Keep track of health check history
        logger.info(f"APIService initialized with base_url={base_url}")

    async def request(self, endpoint: str, method: str = 'GET', params: Dict = None, data: Dict = None) -> str:
        """
        Make a request to the external API service.
        
        :param endpoint: The API endpoint to request.
        :param method: The HTTP method to use (GET, POST, PUT, DELETE).
        :param params: The query parameters for the request.
        :param data: The data to send in the request body.
        :return: The response text from the API.
        """
        logger.debug(f"Requesting {method} {endpoint} with params={params} and data={data}")
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
            logger.debug(f"Cache hit for key={cache_key}")
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
                        logger.error(f"Request to {endpoint} timed out")
                        raise ConnectionError("Request timed out")
                    except aiohttp.ClientError as e:
                        self.metrics.record_error("client_error", str(e))
                        logger.error(f"Client error during request to {endpoint}: {e}")
                        raise ConnectionError(f"Client error: {e}")

    async def _make_request(self, session: aiohttp.ClientSession, method: str, 
                          url: str, headers: Dict, params: Optional[Dict], 
                          data: Optional[Dict]) -> aiohttp.ClientResponse:
        """
        Make an HTTP request using the aiohttp session.
        
        :param session: The aiohttp ClientSession to use.
        :param method: The HTTP method to use.
        :param url: The full URL to request.
        :param headers: The headers to include in the request.
        :param params: The query parameters for the request.
        :param data: The data to send in the request body.
        :return: The aiohttp ClientResponse object.
        """
        logger.debug(f"Making {method} request to {url} with headers={headers} and params={params}")
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
        """
        Handle the HTTP response from the API request.
        
        :param response: The aiohttp ClientResponse object.
        :param endpoint: The API endpoint that was requested.
        :return: The response text from the API.
        """
        logger.debug(f"Handling response for {endpoint} with status {response.status}")
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
            logger.error(f"Response error for {endpoint}: {e.status} {e.message}")
            raise

    def get_health_history(self) -> List[Dict]:
        """
        Return the health check history in a formatted way.
        
        :return: A list of dictionaries representing the health check history.
        """
        logger.debug("Getting health history")
        return [status.to_dict() for status in self.health_history[-10:]]  # Keep last 10 checks

    async def verify_service_health(self, display_results: bool = True) -> bool:
        """
        Verify the health of the service and maintain health history.
        
        :param display_results: Whether to display the health check results.
        :return: True if the service is healthy, False otherwise.
        """
        logger.info(f"Verifying health for service {self.base_url}")
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
        """
        Return a string representation of the service including the last health status.
        
        :return: A string representation of the service.
        """
        status = self._last_health_status
        if status:
            return f"ExternalAPIService({self.base_url}) - Last Check: {status.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - Status: {'Healthy' if status.overall_status else 'Unhealthy'}"
        return f"ExternalAPIService({self.base_url}) - No health check performed yet"
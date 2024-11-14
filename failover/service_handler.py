import logging

logger = logging.getLogger(__name__)

from typing import Optional, Dict
from .service import Service

class ServiceHandler:
    def __init__(self, service: Service, next_handler: Optional['ServiceHandler'] = None):
        logger.debug(f"Initializing ServiceHandler for service {service}")
        self.service = service
        self.next_handler = next_handler

    async def handle(self, endpoint: str, method: str = 'GET', params: Dict = None, data: Dict = None) -> str:
        logger.debug(f"Handling request for endpoint {endpoint} with method {method}")
        if not self.service.circuit_breaker.allow_request(self.service):
            logger.debug(f"Circuit breaker does not allow request for service {self.service}")
            if self.next_handler:
                logger.debug("Passing request to next handler")
                return await self.next_handler.handle(endpoint, method, params, data)
            else:
                logger.error("All services failed.")
                raise Exception("All services failed.")
        try:
            result = await self.service.retry_policy.execute_with_retry(self.service.request, endpoint, method=method, params=params, data=data)
            self.service.circuit_breaker.record_success(self.service)
            logger.info(f"Service {self.service} responded successfully.")
            return result
        except Exception as e:
            self.service.circuit_breaker.record_failure(self.service)
            logger.error(f"Service {self.service} failed with error: {e}.")
            if self.next_handler:
                logger.debug("Passing request to next handler after failure")
                return await self.next_handler.handle(endpoint, method, params, data)
            else:
                logger.error("All services failed.")
                raise Exception("All services failed.")
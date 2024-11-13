import logging

logger = logging.getLogger(__name__)

from typing import Optional, Dict
from .service import Service

class ServiceHandler:
    def __init__(self, service: Service, next_handler: Optional['ServiceHandler'] = None):
        self.service = service
        self.next_handler = next_handler

    async def handle(self, endpoint: str, method: str = 'GET', params: Dict = None, data: Dict = None) -> str:
        if not self.service.circuit_breaker.allow_request(self.service):
            if self.next_handler:
                return await self.next_handler.handle(endpoint, method, params, data)
            else:
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
                return await self.next_handler.handle(endpoint, method, params, data)
            else:
                raise Exception("All services failed.")
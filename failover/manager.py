from asyncio.log import logger
from typing import Dict
from failover.circuit_breaker import CircuitBreaker
from failover.policies import RetryPolicy
from failover.service import Service

class FailoverManager:
    def __init__(self, retry_policy: RetryPolicy, circuit_breaker: CircuitBreaker):
        self.services = []
        self.retry_policy = retry_policy
        self.circuit_breaker = circuit_breaker
        logger.info("FailoverManager initialized")

    def register_service(self, service: Service):
        self.services.append(service)
        logger.info(f"Service {service} registered")

    async def execute(self, endpoint: str, method: str = 'GET', params: Dict = None, data: Dict = None) -> str:
        if not self.services:
            logger.error("No services registered.")
            raise Exception("No services registered.")
        for service in self.services:
            if not self.circuit_breaker.allow_request(service):
                logger.debug(f"Request not allowed for service {service}")
                continue
            try:
                result = await self.retry_policy.execute_with_retry(service.request, endpoint, method=method, params=params, data=data)
                self.circuit_breaker.record_success(service)
                logger.info(f"Service {service} responded successfully.")
                return result
            except Exception as e:
                self.circuit_breaker.record_failure(service)
                logger.error(f"Service {service} failed with error: {e}.")
        logger.error("All services failed.")
        raise Exception("All services failed.")

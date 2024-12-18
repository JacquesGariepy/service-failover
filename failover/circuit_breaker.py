import time
import logging
import configparser
from typing import Dict

from failover.metrics import MetricsCollector
from .service import Service  # Corrected import

logger = logging.getLogger(__name__)

# Load configuration from config file
config = configparser.ConfigParser()
config.read('config.ini')

DEFAULT_FAILURE_THRESHOLD = config.getint('DEFAULT', 'DEFAULT_FAILURE_THRESHOLD', fallback=3)
DEFAULT_RECOVERY_TIME = config.getint('DEFAULT', 'DEFAULT_RECOVERY_TIME', fallback=60)

class CircuitBreaker:
    def __init__(self, failure_threshold: int = DEFAULT_FAILURE_THRESHOLD, recovery_time: int = DEFAULT_RECOVERY_TIME):
        """
        Initialize the CircuitBreaker with a failure threshold and recovery time.
        
        :param failure_threshold: The number of failures before the circuit opens.
        :param recovery_time: The time to wait before attempting to close the circuit.
        """
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failure_counts: Dict[Service, int] = {}
        self.last_failure_time: Dict[Service, float] = {}
        self.state: Dict[Service, str] = {}
        self.metrics = MetricsCollector()
        logger.info(f"CircuitBreaker initialized with failure_threshold={failure_threshold}, recovery_time={recovery_time}")

    async def call(self, service: Service, *args, **kwargs):
        """
        Call the service and manage the circuit state based on the result.
        
        :param service: The service to call.
        :param args: Positional arguments for the service call.
        :param kwargs: Keyword arguments for the service call.
        :return: The result of the service call.
        """
        state = self.state.get(service, 'CLOSED')
        logger.debug(f"Calling service {service} with state {state}")
        if state == 'OPEN':
            time_since_failure = time.time() - self.last_failure_time.get(service, 0)
            if time_since_failure < self.recovery_time:
                raise Exception("Circuit is open")
            else:
                self.state[service] = 'HALF_OPEN'

        try:
            result = await service.call(*args, **kwargs)
            self.state[service] = 'CLOSED'
            self.failure_counts[service] = 0
            logger.info(f"Service {service} call successful")
            return result
        except Exception as e:
            self.failure_counts[service] += 1
            self.last_failure_time[service] = time.time()
            self.metrics.request_counter.labels(
                service=service.__class__.__name__,
                endpoint="unknown",
                status="failure"
            ).inc()
            logger.error(f"Service {service} call failed: {str(e)}")
            if self.failure_counts[service] >= self.failure_threshold:
                self.state[service] = 'OPEN'
            raise e

    def allow_request(self, service: Service) -> bool:
        """
        Check if a request is allowed based on the circuit state.
        
        :param service: The service to check.
        :return: True if the request is allowed, False otherwise.
        """
        state = self.state.get(service, 'CLOSED')
        logger.debug(f"Allow request for service {service} with state {state}")
        if state == 'OPEN':
            time_since_failure = time.time() - self.last_failure_time.get(service, 0)
            if time_since_failure > self.recovery_time:
                self.state[service] = 'HALF_OPEN'
                return True
            else:
                logger.debug(f"Circuit breaker is OPEN for {service}. Skipping request.")
                return False
        return True

    def record_success(self, service: Service):
        """
        Record a successful request and close the circuit if it was open.
        
        :param service: The service that succeeded.
        """
        self.failure_counts[service] = 0
        self.state[service] = 'CLOSED'
        logger.info(f"Service {service} recorded success")

    def record_failure(self, service: Service):
        """
        Record a failed request and open the circuit if the failure threshold is reached.
        
        :param service: The service that failed.
        """
        count = self.failure_counts.get(service, 0) + 1
        self.failure_counts[service] = count
        self.last_failure_time[service] = time.time()
        self.metrics.request_counter.labels(
            service=service.__class__.__name__,
            endpoint="unknown",
            status="failure"
        ).inc()
        if count >= self.failure_threshold:
            self.state[service] = 'OPEN'
            logger.warning(f"Circuit breaker opened for {service}.")
        logger.warning(f"Service {service} recorded failure, count={self.failure_counts[service]}")

    def get_state(self, service: Service) -> str:
        """
        Get the current state of the circuit for the given service.
        
        :param service: The service to check.
        :return: The current state of the circuit.
        """
        return self.state.get(service, 'CLOSED')

    def get_failure_count(self, service: Service) -> int:
        """
        Get the current failure count for the given service.
        
        :param service: The service to check.
        :return: The current failure count.
        """
        return self.failure_counts.get(service, 0)

    def get_last_failure_time(self, service: Service) -> float:
        """
        Get the last failure time for the given service.
        
        :param service: The service to check.
        :return: The last failure time as a timestamp.
        """
        return self.last_failure_time.get(service, 0)

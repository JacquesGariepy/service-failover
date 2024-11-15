from prometheus_client import Counter, Histogram, Gauge
import logging
from typing import ClassVar, Dict, Optional, Protocol

logger = logging.getLogger(__name__)

class MetricsCollector:
    """
    A singleton class to collect and record various metrics for external services.
    """
    _instance: ClassVar[Optional['MetricsCollector']] = None
    _initialized: bool = False
    _metrics: Dict = {}

    def __new__(cls) -> 'MetricsCollector':
        """
        Singleton pattern to ensure only one instance of MetricsCollector exists.
        """
        if cls._instance is None:
            cls._instance = super(MetricsCollector, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initialize the MetricsCollector and set up metrics.
        """
        if not self._initialized:
            self._initialized = True
            self._setup_metrics()

    def _setup_metrics(self) -> None:
        """
        Initialize all metrics once.
        """
        try:
            # Request metrics
            self._metrics['request_counter'] = Counter(
                'external_service_requests_total',
                'Total number of API requests',
                ['service', 'endpoint', 'status']
            )
            
            self._metrics['latency_histogram'] = Histogram(
                'external_service_request_latency_seconds',
                'Request latency in seconds',
                ['service', 'endpoint']
            )
            
            # Health check metrics
            self._metrics['health_check_counter'] = Counter(
                'external_service_health_checks_total',
                'Total number of health checks performed',
                ['service', 'status']
            )
            
            self._metrics['health_status'] = Gauge(
                'external_service_health_status',
                'Current health status of the service (1 = healthy, 0 = unhealthy)',
                ['service']
            )
            
            # Error metrics
            self._metrics['error_counter'] = Counter(
                'external_service_errors_total',
                'Total number of errors by type',
                ['service', 'error_type']
            )
            
            # DNS metrics
            self._metrics['dns_latency'] = Histogram(
                'external_service_dns_resolution_seconds',
                'DNS resolution time in seconds',
                ['service']
            )
            
            # Ping metrics
            self._metrics['ping_latency'] = Histogram(
                'external_service_ping_latency_seconds',
                'Ping latency in seconds',
                ['service']
            )
            
            logger.info("Metrics initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize metrics: {str(e)}")
            raise

    @property
    def request_counter(self) -> Counter:
        """
        Get the request counter metric.
        
        :return: The request counter metric.
        """
        return self._metrics['request_counter']

    @property
    def latency_histogram(self) -> Histogram:
        """
        Get the latency histogram metric.
        
        :return: The latency histogram metric.
        """
        return self._metrics['latency_histogram']

    def record_health_check(self, is_healthy: bool, service_name: str = "unknown") -> None:
        """
        Record the result of a health check.
        
        :param is_healthy: Whether the service is healthy.
        :param service_name: The name of the service.
        """
        try:
            status = "healthy" if is_healthy else "unhealthy"
            self._metrics['health_check_counter'].labels(
                service=service_name,
                status=status
            ).inc()
            self._metrics['health_status'].labels(
                service=service_name
            ).set(1 if is_healthy else 0)
            logger.info(f"Recorded health check for {service_name}: {status}")
        except Exception as e:
            logger.error(f"Failed to record health check metrics: {str(e)}")

    def record_error(self, error_type: str, message: str, service_name: str = "unknown") -> None:
        """
        Record an error occurrence.
        
        :param error_type: The type of error.
        :param message: The error message.
        :param service_name: The name of the service.
        """
        try:
            self._metrics['error_counter'].labels(
                service=service_name,
                error_type=error_type
            ).inc()
            logger.error(f"{error_type} error in {service_name}: {message}")
        except Exception as e:
            logger.error(f"Failed to record error metrics: {str(e)}")

    def record_dns_latency(self, duration: float, service_name: str = "unknown") -> None:
        """
        Record DNS resolution latency.
        
        :param duration: The DNS resolution time in seconds.
        :param service_name: The name of the service.
        """
        try:
            self._metrics['dns_latency'].labels(
                service=service_name
            ).observe(duration)
            logger.info(f"Recorded DNS latency for {service_name}: {duration}s")
        except Exception as e:
            logger.error(f"Failed to record DNS latency metrics: {str(e)}")

    def record_ping_latency(self, duration: float, service_name: str = "unknown") -> None:
        """
        Record ping latency.
        
        :param duration: The ping latency in seconds.
        :param service_name: The name of the service.
        """
        try:
            self._metrics['ping_latency'].labels(
                service=service_name
            ).observe(duration)
            logger.info(f"Recorded ping latency for {service_name}: {duration}s")
        except Exception as e:
            logger.error(f"Failed to record ping latency metrics: {str(e)}")

    def record_request(self, endpoint: str, status: str, service_name: str = "unknown") -> None:
        """
        Record an API request.
        
        :param endpoint: The API endpoint.
        :param status: The status of the request.
        :param service_name: The name of the service.
        """
        try:
            self._metrics['request_counter'].labels(
                service=service_name,
                endpoint=endpoint,
                status=status
            ).inc()
            logger.info(f"Recorded request to {endpoint} for {service_name} with status {status}")
        except Exception as e:
            logger.error(f"Failed to record request metrics: {str(e)}")

from prometheus_client import Counter, Histogram

class MetricsCollector:
    request_counter = Counter('api_requests_total', 'Total requests', ['service', 'endpoint', 'status'])
    latency_histogram = Histogram('api_request_latency_seconds', 'Request latency', ['service', 'endpoint'])
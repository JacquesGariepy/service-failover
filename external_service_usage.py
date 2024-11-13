import asyncio
import configparser
from failover.external_service import ExternalAPIService
from failover.policies import RetryPolicy
from failover.circuit_breaker import CircuitBreaker
from failover.manager import FailoverManager
from dotenv import load_dotenv
import os
from prometheus_client import start_http_server

# Load environment variables from .env file
load_dotenv()

# Load configuration from config file
config = configparser.ConfigParser()
config.read('config.ini')

API_KEY = config.get('DEFAULT', 'API_KEY', fallback='your_api_key')
MAX_ATTEMPTS = config.getint('DEFAULT', 'MAX_ATTEMPTS', fallback=3)
BASE_DELAY = config.getfloat('DEFAULT', 'BASE_DELAY', fallback=1.0)
JITTER = config.getfloat('DEFAULT', 'JITTER', fallback=0.5)
FAILURE_THRESHOLD = config.getint('DEFAULT', 'FAILURE_THRESHOLD', fallback=3)
RECOVERY_TIME = config.getint('DEFAULT', 'RECOVERY_TIME', fallback=60)

async def main():
    # Start metrics server
    start_http_server(8000)
    
    retry_policy = RetryPolicy(max_attempts=MAX_ATTEMPTS, base_delay=BASE_DELAY, jitter=JITTER)
    circuit_breaker = CircuitBreaker(failure_threshold=FAILURE_THRESHOLD, recovery_time=RECOVERY_TIME)
    failover_manager = FailoverManager(retry_policy, circuit_breaker)

    services = [
        ExternalAPIService(
            base_url=config.get('SERVICES', 'EXTERNAL_SERVICE1_BASE_URL', fallback=os.environ.get('EXTERNAL_SERVICE1_BASE_URL', 'https://external1.example.com')),
            api_key=API_KEY
        ),
        ExternalAPIService(
            base_url=config.get('SERVICES', 'EXTERNAL_SERVICE2_BASE_URL', fallback=os.environ.get('EXTERNAL_SERVICE2_BASE_URL', 'https://external2.example.com')),
            api_key=API_KEY
        ),
        ExternalAPIService(
            base_url=config.get('SERVICES', 'EXTERNAL_SERVICE3_BASE_URL', fallback=os.environ.get('EXTERNAL_SERVICE3_BASE_URL', 'https://external3.example.com')),
            api_key=API_KEY
        ),
        ExternalAPIService(
            base_url=config.get('SERVICES', 'EXTERNAL_SERVICE4_BASE_URL', fallback=os.environ.get('EXTERNAL_SERVICE4_BASE_URL', 'https://external3.example.com')),
            api_key=API_KEY
        )
    ]

    for service in services:
        failover_manager.register_service(service)

    # Perform health checks
    for service in services:
        is_healthy = await service.health_check()
        if not is_healthy:
            print(f"Service {service.__class__.__name__} is unhealthy")

    try:
        result = await failover_manager.execute("/products/search", method='GET', params={'q': 'phone'})
        print(result)
    except Exception as e:
        print(f"All services failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
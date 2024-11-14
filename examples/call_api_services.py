import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import configparser
import logging
from failover.api import APIService
from failover.policies import RetryPolicy
from failover.circuit_breaker import CircuitBreaker
from failover.manager import FailoverManager
from dotenv import load_dotenv
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

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("service_failover.log"),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("Service Failover System Initialization")
    logger.info(f"Configuration: Max Attempts: {MAX_ATTEMPTS}, Base Delay: {BASE_DELAY}s, Jitter: {JITTER}s, Failure Threshold: {FAILURE_THRESHOLD}, Recovery Time: {RECOVERY_TIME}s")

    services = [
        APIService(
            base_url=config.get('SERVICES', 'SERVICE1_BASE_URL', 
                              fallback=os.environ.get('SERVICE1_BASE_URL', 'https://dummyjson_error.com/products/search?q=phone')),
            api_key=API_KEY
        ),
        APIService(
            base_url=config.get('SERVICES', 'SERVICE2_BASE_URL', 
                              fallback=os.environ.get('SERVICE2_BASE_URL', 'https://dummyjson_error.com/products/search?q=phone')),
            api_key=API_KEY
        ),
        APIService(
            base_url=config.get('SERVICES', 'SERVICE3_BASE_URL', 
                              fallback=os.environ.get('SERVICE3_BASE_URL', 'https://dummyjson_error.com/products/search?q=phone')),
            api_key=API_KEY
        ),
        APIService(
            base_url=config.get('SERVICES', 'SERVICE4_BASE_URL', 
                              fallback=os.environ.get('SERVICE4_BASE_URL', 'https://dummyjson.com/products/search?q=phone')),
            api_key=API_KEY
        )
    ]

    logger.info("Performing initial health checks...")
    healthy_services = []
    unhealthy_services = []

    for service in services:
        failover_manager.register_service(service)
        is_healthy = await service.verify_service_health(display_results=True)
        
        if is_healthy:
            healthy_services.append(service)
        else:
            unhealthy_services.append(service)

    logger.info(f"Health Check Summary: Total Services: {len(services)}, Healthy Services: {len(healthy_services)}, Unhealthy Services: {len(unhealthy_services)}")

    if unhealthy_services:
        logger.warning("The following services are unhealthy:")
        for service in unhealthy_services:
            logger.warning(f"  - {service}")

    logger.info("Attempting to execute request...")
    try:
        result = await failover_manager.execute("/products/search", 
                                              method='GET', 
                                              params={'q': 'phone'})
        logger.info("Request successful!")
        logger.info(f"Response: {result[:200]}..." if len(result) > 200 else f"Response: {result}")
        print(f"Response: {result[:200]}..." if len(result) > 200 else f"Response: {result}")
    except Exception as e:
        logger.error("All services failed to process the request")
        logger.error(f"Final error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())

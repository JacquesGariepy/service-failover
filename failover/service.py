
from abc import ABC, abstractmethod
import aioping
from .metrics import MetricsCollector
from .cache import Cache
from .connection_pool import ConnectionPool

DEFAULT_DELAY_THRESHOLD = 1.0

class Service(ABC):
    def __init__(self):
        self.metrics = MetricsCollector()
        self.cache = Cache()
        self.connection_pool = ConnectionPool()

    @abstractmethod
    async def request(self) -> str:
        pass

    async def health_check(self) -> bool:
        try:
            delay = await aioping.ping(self.base_url)
            return delay < DEFAULT_DELAY_THRESHOLD
        except:
            return False
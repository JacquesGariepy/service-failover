import logging
from cachetools import TTLCache
import configparser

# Load configuration from config file
config = configparser.ConfigParser()
config.read('config.ini')

DEFAULT_TTL = config.getint('DEFAULT', 'DEFAULT_TTL', fallback=300)

logger = logging.getLogger(__name__)

class Cache:
    def __init__(self, ttl=DEFAULT_TTL):
        self.cache = TTLCache(maxsize=100, ttl=ttl)
        logger.info(f"Cache initialized with TTL={ttl}")

    def get(self, key):
        value = self.cache.get(key)
        logger.debug(f"Cache get: key={key}, value={value}")
        return value

    def set(self, key, value):
        self.cache.setdefault(key, value)
        logger.debug(f"Cache set: key={key}, value={value}")

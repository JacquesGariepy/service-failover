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
        """
        Initialize the Cache with a time-to-live (TTL) value.
        
        :param ttl: The time-to-live for cache entries in seconds.
        """
        self.cache = TTLCache(maxsize=100, ttl=ttl)
        logger.info(f"Cache initialized with TTL={ttl}")

    def get(self, key):
        """
        Retrieve a value from the cache by key.
        
        :param key: The key to look up in the cache.
        :return: The value associated with the key, or None if the key is not found.
        """
        value = self.cache.get(key)
        logger.debug(f"Cache get: key={key}, value={value}")
        return value

    def set(self, key, value):
        """
        Set a value in the cache with the specified key.
        
        :param key: The key to associate with the value.
        :param value: The value to store in the cache.
        """
        self.cache.setdefault(key, value)
        logger.debug(f"Cache set: key={key}, value={value}")

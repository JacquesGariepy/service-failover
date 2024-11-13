
from cachetools import TTLCache

DEFAULT_TTL = 300

class Cache:
    def __init__(self, ttl=DEFAULT_TTL):
        self.cache = TTLCache(maxsize=100, ttl=ttl)

    def get(self, key):
        return self.cache.get(key)

    def set(self, key, value):
        self.cache.setdefault(key, value)
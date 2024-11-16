import asyncio
import logging
import configparser

# Load configuration from config file
config = configparser.ConfigParser()
config.read('config.ini')

DEFAULT_MAX_SIZE = config.getint('DEFAULT', 'DEFAULT_MAX_SIZE', fallback=10)

logger = logging.getLogger(__name__)

class ConnectionPool:
    def __init__(self, max_size=DEFAULT_MAX_SIZE):
        """
        Initialize the ConnectionPool with a maximum size.
        
        :param max_size: The maximum number of concurrent connections.
        """
        self._semaphore = asyncio.Semaphore(max_size)
        self._connections = []
        logger.info(f"ConnectionPool initialized with max_size={max_size}")

    async def acquire(self):
        """
        Acquire a connection from the pool.
        """
        await self._semaphore.acquire()
        logger.debug("Connection acquired")
        # Connection logic here
        return self

    async def release(self):
        """
        Release a connection back to the pool.
        """
        self._semaphore.release()
        logger.debug("Connection released")

    async def __aenter__(self):
        """
        Enter the runtime context related to this object.
        """
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """
        Exit the runtime context related to this object.
        """
        await self.release()

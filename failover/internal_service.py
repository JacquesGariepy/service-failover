
import os
from typing import Dict
from .service import Service

class InternalService(Service):
    def __init__(self, base_url: str = None, api_key: str = None, discontinued: bool = False):
        super().__init__()
        self.base_url = base_url or os.environ.get('DEFAULT_BASE_URL', 'https://default.example.com')
        self.api_key = api_key or os.environ.get('DEFAULT_API_KEY', 'default_api_key')
        self.discontinued = discontinued

    async def request(self, endpoint: str, method: str = 'GET', params: Dict = None, data: Dict = None) -> str:
        if self.discontinued:
            raise ConnectionError("InternalService is discontinued.")
        url = f"{self.base_url}{endpoint}"
        headers = {'Authorization': f"Bearer {self.api_key}"}
        # Simulate a request for demonstration purposes
        return f"Response from {url} with method {method} and headers {headers}"
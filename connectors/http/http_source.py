import asyncio
from typing import Any, Dict, Optional

import aiohttp
from aiohttp_retry import RetryClient, ExponentialRetry

from connectors.source import Source


class HttpSource(Source):
    def __init__(self,
                 default_headers: Optional[Dict[str, str]] = None,
                 retries: int = 3,
                 timeout: int = 5,
                 retry_statuses: Optional[list[int]] = None,
                 backoff_factor: float = 0.5):
        """
        Initialize the HTTP source with retries, timeouts, and retry on specific status codes.
        :param default_headers: Default headers to include in each request
        :param retries: Number of retries for failed requests
        timeout: Timeout in seconds for each request
        :param retry_statuses: List of status codes to retry on
        :param backoff_factor: Factor for exponential backoff retries
        """
        self.default_headers = default_headers or {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
            # noqa: E501
        }
        self.retries = retries  # Number of retries
        self.timeout = timeout  # Timeout in seconds
        self.retry_statuses = retry_statuses or [500, 502, 503, 504]  # Default to server errors

        # Exponential backoff retry strategy
        retry_options = ExponentialRetry(attempts=self.retries, statuses=self.retry_statuses, factor=backoff_factor)
        timeout_setting = aiohttp.ClientTimeout(total=self.timeout)

        # Using RetryClient to automatically handle retries
        self.session = RetryClient(client_session=aiohttp.ClientSession(timeout=timeout_setting),
                                   retry_options=retry_options)

    async def fetch(self, url: str, params: Optional[Dict[str, Any]] = None,
                    headers: Optional[Dict[str, str]] = None) -> bytes:
        """Fetch raw data in bytes from the provided URL."""
        combined_headers = {**self.default_headers, **(headers or {})}

        async with self.session.get(url, params=params, headers=combined_headers) as response:
            response.raise_for_status()  # Raise an error for non-retryable bad responses
            return await response.read()  # Fetch data as raw bytes

    async def close(self):
        """Close the aiohttp session."""
        await self.session.close()  # Ensure the underlying session is closed


# Example usage
async def main():
    http_source = HttpSource(default_headers={"User-Agent": "MyHttpSource/1.0"}, retries=3, timeout=10)
    try:
        # Example API call
        url = "https://api.example.com/data"  # Replace with your API endpoint
        params = {"key": "value"}  # Example query parameters if needed
        headers = {"Authorization": "Bearer YOUR_TOKEN"}  # Example headers if needed

        raw_data = await http_source.fetch(url, params=params, headers=headers)
        print(f"Fetched {len(raw_data)} bytes of data")
    finally:
        await http_source.close()


if __name__ == '__main__':
    asyncio.run(main())

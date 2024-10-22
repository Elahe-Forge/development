import asyncio
import unittest
from unittest.mock import patch, AsyncMock

from connectors.http.http_source import HttpSource


class TestHttpSource(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.http_source = HttpSource()

    async def test_fetch_success(self):
        # Create a mock response object
        mock_response = AsyncMock()
        mock_response.read.return_value = b'{"key": "value"}'

        # Make the mock response behave like an async context manager
        mock_response.__aenter__.return_value = mock_response

        # Mock the session.get method to return the mock response
        with patch.object(self.http_source.session, 'get', return_value=mock_response) as mock_get:
            raw_data = await self.http_source.fetch('https://api.example.com/data')
            self.assertEqual(raw_data, b'{"key": "value"}')  # Check if the data fetched is correct

    async def test_fetch_retry_on_500(self):
        mock_response = AsyncMock()
        mock_response.read = AsyncMock(side_effect=Exception("Server Error"))
        mock_response.status = 500

        # Make the mock response behave like an async context manager
        mock_response.__aenter__.return_value = mock_response

        with patch.object(self.http_source.session, 'get', side_effect=[mock_response, mock_response, mock_response]):
            with self.assertRaises(Exception):
                await self.http_source.fetch('https://api.example.com/data')

    async def test_fetch_retry_on_503(self):
        mock_response = AsyncMock()
        mock_response.read = AsyncMock(side_effect=Exception("Service Unavailable"))
        mock_response.status = 503

        # Make the mock response behave like an async context manager
        mock_response.__aenter__.return_value = mock_response

        with patch.object(self.http_source.session, 'get', side_effect=[mock_response, mock_response, mock_response]):
            with self.assertRaises(Exception):
                await self.http_source.fetch('https://api.example.com/data')

    async def test_fetch_with_custom_headers(self):
        mock_response = AsyncMock()
        mock_response.read.return_value = b'{"key": "value"}'

        # Make the mock response behave like an async context manager
        mock_response.__aenter__.return_value = mock_response

        with patch.object(self.http_source.session, 'get', return_value=mock_response):
            headers = {"Authorization": "Bearer YOUR_TOKEN"}
            raw_data = await self.http_source.fetch('https://api.example.com/data', headers=headers)
            self.assertEqual(raw_data, b'{"key": "value"}')  # Check if the data fetched is correct

    async def test_fetch_with_query_params(self):
        mock_response = AsyncMock()
        mock_response.read.return_value = b'{"key": "value"}'

        # Make the mock response behave like an async context manager
        mock_response.__aenter__.return_value = mock_response

        with patch.object(self.http_source.session, 'get', return_value=mock_response):
            raw_data = await self.http_source.fetch('https://api.example.com/data', params={'key': 'value'})
            self.assertEqual(raw_data, b'{"key": "value"}')  # Check if the data fetched is correct

    async def test_fetch_timeout(self):
        self.http_source = HttpSource(timeout=0.001)  # Very short timeout
        mock_response = AsyncMock()
        mock_response.read.side_effect = asyncio.TimeoutError  # Simulate a timeout

        # Make the mock response behave like an async context manager
        mock_response.__aenter__.return_value = mock_response

        with patch.object(self.http_source.session, 'get', return_value=mock_response):
            with self.assertRaises(asyncio.TimeoutError):
                await self.http_source.fetch('https://api.example.com/data')

    async def test_close_session(self):
        await self.http_source.close()  # Should not raise any errors


if __name__ == '__main__':
    unittest.main()

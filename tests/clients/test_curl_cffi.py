from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from xcrap.clients.curl_cffi import CurlCffiClient
from xcrap.core.errors import DependencyMissingError


def test_curl_cffi_missing_dependency():
    with patch("xcrap.clients.curl_cffi.AsyncSession", None):
        with pytest.raises(DependencyMissingError) as exc_info:
            CurlCffiClient()
        assert "curl-cffi" in str(exc_info.value)
        assert "xcrap[curl]" in str(exc_info.value)


@pytest.mark.asyncio
async def test_curl_cffi_fetch_mocked():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.reason = "OK"
    mock_response.text = "<html><body>Anti-Bot Passed</body></html>"
    mock_response.headers = {"content-type": "text/html"}

    mock_session = AsyncMock()
    mock_session.request.return_value = mock_response

    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_session

    with patch("xcrap.clients.curl_cffi.AsyncSession", mock_session_cls):
        client = CurlCffiClient(impersonate="chrome120")
        resp = await client.fetch(url="https://secure.example.com")

        assert resp.status == 200
        assert "Anti-Bot Passed" in resp.body
        assert resp.headers["content-type"] == "text/html"


@pytest.mark.asyncio
async def test_curl_cffi_fetch_many_mocked():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.reason = "OK"
    mock_response.text = "item"
    mock_response.headers = {}

    mock_session = AsyncMock()
    mock_session.request.return_value = mock_response

    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_session

    with patch("xcrap.clients.curl_cffi.AsyncSession", mock_session_cls):
        client = CurlCffiClient()
        responses = await client.fetch_many(
            requests=[
                {"url": "https://a.com", "method": "GET", "retries": 0, "max_retries": 0, "retry_delay": 0, "headers": None},
                {"url": "https://b.com", "method": "GET", "retries": 0, "max_retries": 0, "retry_delay": 0, "headers": None},
            ],
            concurrency=2,
            request_delay=None,
        )
        assert len(responses) == 2

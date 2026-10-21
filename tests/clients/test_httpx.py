import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from xcrap.clients.httpx import HttpxClient


@pytest.mark.asyncio
async def test_httpx_client_fetch_success() -> None:
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_instance = mock_client_class.return_value
        mock_instance.request = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.reason_phrase = "OK"
        mock_response.text = "Success"
        mock_response.headers = {"Content-Type": "text/plain"}

        mock_instance.request.return_value = mock_response

        client = HttpxClient()
        response = await client.fetch("http://test.com")

        assert response.status == 200
        assert response.body == "Success"
        assert response.attempts == 1
        mock_instance.request.assert_called_once()


@pytest.mark.asyncio
async def test_httpx_client_fetch_with_proxy() -> None:
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_instance = mock_client_class.return_value
        mock_instance.request = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_instance.request.return_value = mock_response

        client = HttpxClient(proxy_url="http://proxy/")
        await client.fetch("http://test.com")

        mock_instance.request.assert_called_with(
            method="GET", url="http://proxy/http://test.com", headers={"User-Agent": client._current_user_agent}
        )


@pytest.mark.asyncio
async def test_httpx_client_fetch_retry_on_failure() -> None:
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_instance = mock_client_class.return_value
        mock_instance.request = AsyncMock()

        mock_error_response = MagicMock(spec=httpx.Response)
        mock_error_response.status_code = 404
        mock_error_response.reason_phrase = "Not Found"
        mock_error_response.text = "Error"
        mock_error_response.headers = {}
        mock_error_response.request = MagicMock()

        # First call fails with 404 (which raises HTTPStatusError in our code)
        # Second call succeeds
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.reason_phrase = "OK"
        mock_success_response.text = "Perfect"
        mock_success_response.headers = {}

        mock_instance.request.side_effect = [mock_error_response, mock_success_response]

        client = HttpxClient()

        response = await client.fetch("http://test.com", max_retries=1, retry_delay=1)

        assert response.status == 200
        assert response.body == "Perfect"
        assert response.attempts == 2
        assert len(response.failed_attempts) == 1
        assert "Invalid status code: 404" in response.failed_attempts[0]["error"]


@pytest.mark.asyncio
async def test_httpx_client_fetch_max_retries_exceeded() -> None:
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_instance = mock_client_class.return_value
        mock_instance.request = AsyncMock()

        mock_instance.request.side_effect = Exception("Network Error")

        client = HttpxClient()
        response = await client.fetch("http://test.com", max_retries=1)

        assert response.status == 500
        assert response.status_text == "Request Failed"
        assert "Network Error" in response.body
        assert response.attempts == 2
        assert len(response.failed_attempts) == 2


@pytest.mark.asyncio
async def test_httpx_client_fetch_status_error_no_retries() -> None:
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_instance = mock_client_class.return_value
        mock_instance.request = AsyncMock()

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 403
        mock_resp.reason_phrase = "Forbidden"
        mock_resp.text = "No access"
        mock_resp.headers = {"X-Error": "True"}
        mock_resp.request = MagicMock()

        mock_instance.request.return_value = mock_resp

        client = HttpxClient()
        response = await client.fetch("http://test.com", max_retries=0)

        assert response.status == 403
        assert response.body == "No access"
        assert response.headers["x-error"] == "True"


@pytest.mark.asyncio
async def test_httpx_client_fetch_many() -> None:
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_instance = mock_client_class.return_value
        mock_instance.request = AsyncMock()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.reason_phrase = "OK"
        mock_resp.text = "Data"
        mock_resp.headers = {}
        mock_instance.request.return_value = mock_resp

        client = HttpxClient()
        requests = [{"url": "http://1.com", "method": "GET"}, {"url": "http://2.com", "method": "GET"}]
        results = await client.fetch_many(requests, request_delay=None, concurrency=2)

        assert len(results) == 2
        assert results[0].body == "Data"
        assert results[1].body == "Data"


@pytest.mark.asyncio
async def test_httpx_client_fetch_many_with_concurrency() -> None:
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_instance = mock_client_class.return_value

        async def slow_request(*args, **kwargs):
            await asyncio.sleep(0.05)
            m = MagicMock()
            m.status_code = 200
            m.reason_phrase = "OK"
            m.text = "Slow"
            m.headers = {}
            return m

        mock_instance.request.side_effect = slow_request

        client = HttpxClient()
        requests = [{"url": f"http://{i}.com"} for i in range(4)]
        results = await client.fetch_many(requests, request_delay=None, concurrency=2)

        assert len(results) == 4
        for r in results:
            assert r.body == "Slow"


@pytest.mark.asyncio
async def test_httpx_client_fetch_many_hit_gather() -> None:
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_instance = mock_client_class.return_value
        mock_instance.request = AsyncMock()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.reason_phrase = "OK"
        mock_resp.text = "Data"
        mock_resp.headers = {}
        mock_instance.request.return_value = mock_resp

        client = HttpxClient()
        requests = [{"url": "http://1.com"}]
        # No concurrency limit, so len(executing) < concurrency (None)
        # It should exit the loop with 1 task in executing and hit line 123
        results = await client.fetch_many(requests, request_delay=None, concurrency=None)

        assert len(results) == 1
        assert results[0].body == "Data"


@pytest.mark.asyncio
async def test_httpx_client_proxy_url() -> None:
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_instance = mock_client_class.return_value
        mock_instance.request = AsyncMock()
        mock_instance.request.return_value = MagicMock(status_code=200, reason_phrase="OK", text="ok", headers={})

        client = HttpxClient(proxy_url="http://proxy/")
        await client.fetch(url="http://test.com")

        mock_instance.request.assert_called_once()
        args, kwargs = mock_instance.request.call_args
        assert kwargs["url"] == "http://proxy/http://test.com"


@pytest.mark.asyncio
async def test_httpx_client_custom_headers() -> None:
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_instance = mock_client_class.return_value
        mock_instance.request = AsyncMock()
        mock_instance.request.return_value = MagicMock(status_code=200, reason_phrase="OK", text="ok", headers={})

        client = HttpxClient()
        await client.fetch(url="http://test.com", headers={"X-Test": "Value"})

        mock_instance.request.assert_called_once()
        args, kwargs = mock_instance.request.call_args
        assert kwargs["headers"]["X-Test"] == "Value"
        assert "User-Agent" in kwargs["headers"]

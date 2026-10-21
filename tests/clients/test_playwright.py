from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xcrap.clients.playwright import PlaywrightClient
from xcrap.core.errors import DependencyMissingError


def test_playwright_missing_dependency():
    with patch("xcrap.clients.playwright.async_playwright", None):
        with pytest.raises(DependencyMissingError) as exc_info:
            PlaywrightClient()
        assert "playwright" in str(exc_info.value)
        assert "xcrap[playwright]" in str(exc_info.value)


@pytest.mark.asyncio
async def test_playwright_fetch_mocked():
    mock_page = AsyncMock()
    mock_page.content.return_value = "<html><body><h1>SPA Loaded</h1></body></html>"

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.all_headers.return_value = {"content-type": "text/html"}
    mock_page.goto.return_value = mock_resp

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context

    mock_playwright_instance = AsyncMock()
    mock_playwright_instance.chromium.launch.return_value = mock_browser

    mock_playwright_cm = MagicMock()
    mock_playwright_cm.return_value.__aenter__.return_value = mock_playwright_instance

    action_executed = False

    async def custom_action(page):
        nonlocal action_executed
        action_executed = True

    with patch("xcrap.clients.playwright.async_playwright", mock_playwright_cm):
        client = PlaywrightClient()
        response = await client.fetch(
            url="https://spa.example.com",
            actions=[
                {"type": "before_request", "func": custom_action},
                custom_action,
            ],
        )

        assert response.status == 200
        assert "SPA Loaded" in response.body
        assert action_executed is True


@pytest.mark.asyncio
async def test_playwright_fetch_many_mocked():
    mock_page = AsyncMock()
    mock_page.content.return_value = "<html>Item</html>"

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.all_headers.return_value = {}
    mock_page.goto.return_value = mock_resp

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context

    mock_playwright_instance = AsyncMock()
    mock_playwright_instance.chromium.launch.return_value = mock_browser

    mock_playwright_cm = MagicMock()
    mock_playwright_cm.return_value.__aenter__.return_value = mock_playwright_instance

    with patch("xcrap.clients.playwright.async_playwright", mock_playwright_cm):
        client = PlaywrightClient()
        responses = await client.fetch_many(
            requests=[
                {"url": "https://a.com", "method": "GET", "retries": 0, "max_retries": 0, "retry_delay": 0, "headers": None},
            ],
            concurrency=1,
            request_delay=None,
        )
        assert len(responses) == 1

from unittest.mock import MagicMock, patch
import pytest

from xcrap.clients.selenium import SeleniumClient
from xcrap.core.errors import DependencyMissingError


def test_selenium_missing_dependency():
    with patch("xcrap.clients.selenium.webdriver", None):
        with pytest.raises(DependencyMissingError) as exc_info:
            SeleniumClient()
        assert "selenium" in str(exc_info.value)
        assert "xcrap[selenium]" in str(exc_info.value)


@pytest.mark.asyncio
async def test_selenium_fetch_mocked():
    mock_driver = MagicMock()
    mock_driver.page_source = "<html><body><h1>Selenium Rendered</h1></body></html>"

    action_executed = False

    def sample_action(driver):
        nonlocal action_executed
        action_executed = True

    mock_webdriver = MagicMock()
    mock_webdriver.Chrome.return_value = mock_driver

    with patch("xcrap.clients.selenium.webdriver", mock_webdriver):
        client = SeleniumClient(browser_type="chrome", headless=True)
        response = await client.fetch(
            url="https://selenium.example.com",
            actions=[
                {"type": "before_request", "func": sample_action},
                sample_action,
            ],
        )

        assert response.status == 200
        assert "Selenium Rendered" in response.body
        assert action_executed is True
        mock_driver.get.assert_called_once_with("https://selenium.example.com")
        mock_driver.quit.assert_called_once()


@pytest.mark.asyncio
async def test_selenium_firefox_and_edge_browsers():
    mock_driver = MagicMock()
    mock_driver.page_source = "<html>Firefox/Edge</html>"

    mock_webdriver = MagicMock()
    mock_webdriver.Firefox.return_value = mock_driver
    mock_webdriver.Edge.return_value = mock_driver

    with patch("xcrap.clients.selenium.webdriver", mock_webdriver):
        client_firefox = SeleniumClient(browser_type="firefox", proxy="http://proxy:8080")
        resp_ff = await client_firefox.fetch("https://firefox.com")
        assert resp_ff.status == 200

        client_edge = SeleniumClient(browser_type="edge", user_agent="CustomEdge")
        resp_edge = await client_edge.fetch("https://edge.com")
        assert resp_edge.status == 200


@pytest.mark.asyncio
async def test_selenium_fetch_many_mocked():
    mock_driver = MagicMock()
    mock_driver.page_source = "<html>Page</html>"

    mock_webdriver = MagicMock()
    mock_webdriver.Chrome.return_value = mock_driver

    with patch("xcrap.clients.selenium.webdriver", mock_webdriver):
        client = SeleniumClient()
        responses = await client.fetch_many(
            requests=[
                {"url": "https://a.com", "method": "GET", "retries": 0, "max_retries": 0, "retry_delay": 0, "headers": None},
                {"url": "https://b.com", "method": "GET", "retries": 0, "max_retries": 0, "retry_delay": 0, "headers": None},
            ],
            concurrency=2,
            request_delay=None,
        )
        assert len(responses) == 2


@pytest.mark.asyncio
async def test_selenium_fetch_failure_retries():
    mock_webdriver = MagicMock()
    mock_webdriver.Chrome.side_effect = Exception("Driver crash")

    with patch("xcrap.clients.selenium.webdriver", mock_webdriver):
        client = SeleniumClient()
        resp = await client.fetch(url="https://fail.com", max_retries=1, retry_delay=10)

        assert resp.status == 500
        assert "Driver crash" in resp.status_text
        assert resp.attempts == 2

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xcrap.clients.curl_cffi import CurlCffiClient
from xcrap.clients.playwright import PlaywrightClient
from xcrap.clients.selenium import SeleniumClient
from xcrap.clients.seleniumbase import SeleniumBaseClient
from xcrap.core.errors import DependencyMissingError

TWO_REQUESTS = [{"url": "https://a.test"}, {"url": "https://b.test"}]


# ---- curl-cffi ------------------------------------------------------------------------------------------------


def curl_session(response=None, error=None):
    session = AsyncMock()

    if error:
        session.request.side_effect = error
    else:
        session.request.return_value = response

    session_cls = MagicMock()
    session_cls.return_value.__aenter__.return_value = session

    return session_cls, session


def curl_response():
    return MagicMock(status_code=200, reason="OK", text="ok", headers={})


@pytest.mark.asyncio
async def test_curl_cffi_fetch_requires_dependency_at_call_time():
    with patch("xcrap.clients.curl_cffi.AsyncSession", MagicMock()):
        client = CurlCffiClient()

    with patch("xcrap.clients.curl_cffi.AsyncSession", None):
        with pytest.raises(DependencyMissingError):
            await client.fetch("https://a.test")


@pytest.mark.asyncio
async def test_curl_cffi_merges_headers_and_retries_until_failure():
    session_cls, session = curl_session(response=curl_response())

    with patch("xcrap.clients.curl_cffi.AsyncSession", session_cls):
        await CurlCffiClient().fetch("https://a.test", headers={"X-A": "1"})

    assert session.request.call_args.kwargs["headers"]["X-A"] == "1"

    session_cls, session = curl_session(error=Exception("boom"))

    with patch("xcrap.clients.curl_cffi.AsyncSession", session_cls):
        response = await CurlCffiClient().fetch("https://a.test", max_retries=1, retry_delay=1)

    assert response.status == 500
    assert "boom" in response.status_text
    assert response.attempts == 2


@pytest.mark.asyncio
async def test_curl_cffi_fetch_many_respects_concurrency():
    session_cls, _ = curl_session(response=curl_response())

    with patch("xcrap.clients.curl_cffi.AsyncSession", session_cls):
        responses = await CurlCffiClient().fetch_many(TWO_REQUESTS, request_delay=None, concurrency=1)

    assert len(responses) == 2


# ---- playwright -----------------------------------------------------------------------------------------------


def playwright_stack(goto_error=None):
    page = AsyncMock()
    page.content.return_value = "<html>ok</html>"
    response = AsyncMock(status=200)
    response.all_headers.return_value = {}

    if goto_error:
        page.goto.side_effect = goto_error
    else:
        page.goto.return_value = response

    context = AsyncMock()
    context.new_page.return_value = page
    browser = AsyncMock()
    browser.new_context.return_value = context
    instance = AsyncMock()
    instance.chromium.launch.return_value = browser
    factory = MagicMock()
    factory.return_value.__aenter__.return_value = instance

    return factory, page


@pytest.mark.asyncio
async def test_playwright_fetch_requires_dependency_at_call_time():
    factory, _ = playwright_stack()

    with patch("xcrap.clients.playwright.async_playwright", factory):
        client = PlaywrightClient()

    with patch("xcrap.clients.playwright.async_playwright", None):
        with pytest.raises(DependencyMissingError):
            await client.fetch("https://a.test")


@pytest.mark.asyncio
async def test_playwright_after_request_dict_action_may_be_async():
    factory, _ = playwright_stack()
    ran = []

    async def action(page):
        ran.append("async")

    def sync_action(page):
        ran.append("sync")

    with patch("xcrap.clients.playwright.async_playwright", factory):
        await PlaywrightClient().fetch(
            "https://a.test",
            actions=[
                {"type": "after_request", "func": action},
                {"type": "action", "exec": sync_action},
                {"type": "after_request"},
            ],
        )

    assert ran == ["async", "sync"]


@pytest.mark.asyncio
async def test_playwright_failure_retries_then_returns_500():
    factory, page = playwright_stack(goto_error=Exception("nav failed"))

    with patch("xcrap.clients.playwright.async_playwright", factory):
        response = await PlaywrightClient().fetch("https://a.test", max_retries=1, retry_delay=1)

    assert response.status == 500
    assert "nav failed" in response.status_text
    assert page.goto.call_count == 2


@pytest.mark.asyncio
async def test_playwright_fetch_many_respects_concurrency():
    factory, _ = playwright_stack()

    with patch("xcrap.clients.playwright.async_playwright", factory):
        responses = await PlaywrightClient().fetch_many(TWO_REQUESTS, request_delay=None, concurrency=1)

    assert len(responses) == 2


# ---- selenium -------------------------------------------------------------------------------------------------


def selenium_patches(driver):
    webdriver = MagicMock()
    webdriver.Chrome.return_value = driver
    webdriver.Edge.return_value = driver
    webdriver.Firefox.return_value = driver

    return (
        patch("xcrap.clients.selenium.webdriver", webdriver),
        patch("xcrap.clients.selenium.ChromeOptions", MagicMock()),
        patch("xcrap.clients.selenium.EdgeOptions", MagicMock()),
        patch("xcrap.clients.selenium.FirefoxOptions", MagicMock()),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("browser", ["chrome", "edge"])
async def test_selenium_applies_proxy_and_after_request_dict_actions(browser):
    driver = MagicMock(page_source="<html></html>")
    seen = []
    patches = selenium_patches(driver)

    with patches[0], patches[1], patches[2], patches[3]:
        client = SeleniumClient(browser_type=browser, proxy_url="http://proxy:8080")
        response = await client.fetch(
            "https://a.test",
            actions=[{"type": "after_request", "func": lambda d: seen.append(d)}, {"type": "after_request"}],
        )

    assert response.status == 200
    assert seen == [driver]


@pytest.mark.asyncio
async def test_selenium_fetch_requires_dependency_at_call_time():
    patches = selenium_patches(MagicMock())

    with patches[0], patches[1], patches[2], patches[3]:
        client = SeleniumClient()

    with patch("xcrap.clients.selenium.webdriver", None):
        with pytest.raises(DependencyMissingError):
            await client.fetch("https://a.test")


@pytest.mark.asyncio
async def test_selenium_fetch_many_respects_concurrency():
    driver = MagicMock(page_source="<html></html>")
    patches = selenium_patches(driver)

    with patches[0], patches[1], patches[2], patches[3]:
        responses = await SeleniumClient().fetch_many(TWO_REQUESTS, request_delay=None, concurrency=1)

    assert len(responses) == 2


# ---- seleniumbase ---------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seleniumbase_after_request_dict_actions_and_missing_dependency():
    driver = MagicMock(page_source="<html></html>")
    seen = []

    with patch("xcrap.clients.seleniumbase.Driver", return_value=driver):
        client = SeleniumBaseClient()
        await client.fetch(
            "https://a.test",
            actions=[{"type": "after_request", "func": lambda d: seen.append(d)}, {"type": "after_request"}],
        )

    assert seen == [driver]

    with patch("xcrap.clients.seleniumbase.Driver", None):
        with pytest.raises(DependencyMissingError):
            await client.fetch("https://a.test")

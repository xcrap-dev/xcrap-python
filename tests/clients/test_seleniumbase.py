from unittest.mock import MagicMock, patch

import pytest

from xcrap.clients.seleniumbase import SeleniumBaseClient
from xcrap.core.errors import DependencyMissingError


def test_seleniumbase_missing_dependency():
    with patch("xcrap.clients.seleniumbase.Driver", None):
        with pytest.raises(DependencyMissingError) as exc_info:
            SeleniumBaseClient()

        assert "xcrap[seleniumbase]" in str(exc_info.value)


@pytest.mark.asyncio
async def test_seleniumbase_uc_fetch_runs_actions_in_order():
    driver = MagicMock()
    driver.page_source = "<html><h1>SB</h1></html>"
    calls = []
    driver.uc_open_with_reconnect.side_effect = lambda *a: calls.append("open")

    with patch("xcrap.clients.seleniumbase.Driver", return_value=driver) as factory:
        client = SeleniumBaseClient(reconnect_time=1.5, user_agent="ua/1", proxy_url="http://user:pw@host:3128")
        response = await client.fetch(
            "https://site.test",
            actions=[
                {"type": "before_request", "func": lambda d: calls.append("before")},
                lambda d: calls.append("after"),
            ],
        )

    assert response.status == 200
    assert "SB" in response.body
    assert calls == ["before", "open", "after"]
    driver.uc_open_with_reconnect.assert_called_once_with("https://site.test", 1.5)
    driver.quit.assert_called_once()

    kwargs = factory.call_args.kwargs
    assert kwargs["uc"] is True
    assert kwargs["agent"] == "ua/1"
    assert kwargs["proxy"] == "user:pw@host:3128"  # scheme stripped


@pytest.mark.asyncio
async def test_seleniumbase_without_uc_uses_plain_get_and_driver_options():
    driver = MagicMock()
    driver.page_source = "<html></html>"

    with patch("xcrap.clients.seleniumbase.Driver", return_value=driver) as factory:
        client = SeleniumBaseClient(uc=False, headless=False, driver_options={"incognito": True})
        await client.fetch("https://site.test")

    driver.get.assert_called_once_with("https://site.test")
    driver.uc_open_with_reconnect.assert_not_called()
    assert factory.call_args.kwargs["incognito"] is True
    assert factory.call_args.kwargs["headless"] is False


@pytest.mark.asyncio
async def test_seleniumbase_failure_retries_then_returns_500():
    with patch("xcrap.clients.seleniumbase.Driver", side_effect=Exception("Driver crash")) as factory:
        response = await SeleniumBaseClient().fetch("https://fail.test", max_retries=1, retry_delay=1)

    assert response.status == 500
    assert "Driver crash" in response.status_text
    assert response.attempts == 2
    assert factory.call_count == 2


@pytest.mark.asyncio
async def test_seleniumbase_fetch_many_keeps_order():
    driver = MagicMock()
    driver.page_source = "<html></html>"

    with patch("xcrap.clients.seleniumbase.Driver", return_value=driver):
        responses = await SeleniumBaseClient().fetch_many(
            [{"url": "https://a.test"}, {"url": "https://b.test"}], request_delay=None, concurrency=1
        )

    assert [r.status for r in responses] == [200, 200]

"""
JavaScript-rendered pages with PlaywrightClient (quotes.toscrape.com/js-delayed/).

The quotes are injected by JavaScript ~10 seconds after load, so an HTTP client sees an empty page.
Requires: pip install "xcrap[playwright]" && playwright install chromium

    poetry run python examples/12_client_playwright.py
"""

import asyncio

from xcrap.clients import HttpxClient, PlaywrightClient
from xcrap.extractor import css

URL = "https://quotes.toscrape.com/js-delayed/"


async def main() -> None:
    http = await HttpxClient().fetch(url=URL)
    print("httpx quotes     :", len(http.as_html_parser().extract_values(css("div.quote"))))

    client = PlaywrightClient(headless=True, timeout=30_000)
    response = await client.fetch(
        url=URL,
        # Actions run after navigation; they may be sync or async and receive the Playwright page.
        actions=[lambda page: page.wait_for_selector("div.quote", timeout=20_000)],
    )

    parser = response.as_html_parser()
    print("playwright quotes:", len(parser.extract_values(css("div.quote"))))
    print("first author     :", parser.extract_value(css("small.author::text")))


if __name__ == "__main__":
    asyncio.run(main())

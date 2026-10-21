"""
A spider that renders JavaScript (quotes.toscrape.com/js/ and /js-delayed/) with PlaywrightClient.

Spiders take any HttpClientBase, so swapping the client is all it takes. To pass browser actions on every
request we subclass the client and fill them in. Requires: pip install "xcrap[playwright]" && playwright install chromium

    poetry run python examples/25_spider_playwright.py
"""

import asyncio

from xcrap.clients import PlaywrightClient
from xcrap.extractor import css
from xcrap.spiders import Request, Spider


class WaitForQuotesClient(PlaywrightClient):
    async def fetch(self, *args, **kwargs):
        kwargs.setdefault("actions", [lambda page: page.wait_for_selector("div.quote", timeout=20_000)])

        return await super().fetch(*args, **kwargs)


class JsQuotesSpider(Spider):
    name = "js-quotes"
    concurrency = 1  # one browser at a time keeps the demo light

    async def start_requests(self):
        yield Request("https://quotes.toscrape.com/js/")

    async def parse(self, response):
        parser = response.as_html_parser()

        for quote in parser.extract_values(css("div.quote span.text::text")):
            yield {"text": quote}

        for href in parser.extract_values(css("li.next a::attr(href)")):
            yield response.follow(href)


async def main() -> None:
    spider = JsQuotesSpider(client=WaitForQuotesClient(headless=True), max_requests=2)
    quotes = await spider.collect()

    print(f"{len(quotes)} quotes from {spider.stats.requests_made} rendered pages")
    print(quotes[0])


if __name__ == "__main__":
    asyncio.run(main())

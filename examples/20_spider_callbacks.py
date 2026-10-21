"""
A spider with callbacks (quotes.toscrape.com): list pages -> author pages.

Shows: Spider, parse() as an async generator, response.follow(), named callbacks,
settings (concurrency, request_delay, max_requests), SpiderStats, collect().

    poetry run python examples/20_spider_callbacks.py
"""

import asyncio
import logging

from xcrap.extractor import css
from xcrap.spiders import Spider

logging.basicConfig(level=logging.WARNING)


class AuthorsSpider(Spider):
    name = "authors"
    start_urls = ["https://quotes.toscrape.com"]
    concurrency = 4
    request_delay = 100  # ms between request starts
    max_requests = 15  # hard cap on scheduled requests

    async def parse(self, response):
        parser = response.as_html_parser()

        # Requests are followed; everything else you yield is an item.
        for href in parser.extract_values(css("div.quote span a::attr(href)")):
            yield response.follow(href, callback="parse_author")

        for href in parser.extract_values(css("li.next a::attr(href)")):
            yield response.follow(href)  # same callback (parse) by default

    def parse_author(self, response):
        parser = response.as_html_parser()

        # Callbacks may also simply return an item (or a list, or a coroutine...).
        return {
            "name": parser.extract_value(css("h3.author-title::text")),
            "born": parser.extract_value(css("span.author-born-date::text")),
            "url": response.url,
        }


async def main() -> None:
    spider = AuthorsSpider()
    authors = await spider.collect()  # runs the crawl and returns every item

    print(f"{len(authors)} authors:")
    for author in authors[:5]:
        print(f"  {author['name']} (born {author['born']})")

    stats = spider.stats
    print(f"requests={stats.requests_made} filtered={stats.requests_filtered} dropped={stats.requests_dropped}")
    print(f"finished in {stats.elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())

"""
A declarative spider (quotes.toscrape.com): no parse() at all.

ModelSpider extracts `model` from every page (once per `items_query` match) and follows `follow_query`.

    poetry run python examples/22_spider_declarative.py
"""

import asyncio

from xcrap.extractor import HtmlBaseField, HtmlExtractionModel, css
from xcrap.spiders import ModelSpider


class QuoteModel(HtmlExtractionModel):
    text = HtmlBaseField(query=css("span.text::text"))
    author = HtmlBaseField(query=css("small.author::text"))
    tags = HtmlBaseField(query=css("a.tag::text"), multiple=True)


class QuotesSpider(ModelSpider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com"]
    model = QuoteModel
    items_query = css("div.quote")
    follow_query = css("li.next a::attr(href)")
    concurrency = 4
    max_depth = 3  # start page is depth 0, so this crawls 4 pages


async def main() -> None:
    # stream() yields items as soon as they are scraped, while the crawl is still running.
    count = 0

    async for quote in QuotesSpider().stream():
        count += 1
        if count <= 3:
            print(f"{quote['author']}: {quote['tags']}")

    print(f"{count} quotes")


if __name__ == "__main__":
    asyncio.run(main())

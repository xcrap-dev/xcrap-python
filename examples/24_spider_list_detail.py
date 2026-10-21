"""
Listing -> detail crawl with metadata, priorities and error handling (books.toscrape.com).

Shows: meta, priority, errback, on_close, settings passed to the constructor, SpiderStats.

    poetry run python examples/24_spider_list_detail.py
"""

import asyncio
import re

from xcrap.extractor import HtmlBaseField, HtmlExtractionModel, css
from xcrap.spiders import Spider


class BookDetailModel(HtmlExtractionModel):
    title = HtmlBaseField(query=css("div.product_main h1::text"))
    price = HtmlBaseField(query=css("p.price_color::text"), extractor=lambda el: float(re.search(r"\d+\.\d+", el.get())[0]))
    upc = HtmlBaseField(query=css("table.table-striped tr:nth-child(1) td::text"))
    description = HtmlBaseField(query=css("#product_description + p::text"), default="")


class BooksSpider(Spider):
    name = "books"
    start_urls = ["https://books.toscrape.com/catalogue/category/books/mystery_3/index.html"]

    async def parse(self, response):
        parser = response.as_html_parser()
        category = parser.extract_value(css("div.page-header h1::text"))

        for href in parser.extract_values(css("article.product_pod h3 a::attr(href)")):
            yield response.follow(
                href,
                callback="parse_book",
                errback="book_failed",
                meta={"category": category},  # travels with the request
                priority=10,  # details first, before more listing pages
            )

        for href in parser.extract_values(css("li.next a::attr(href)")):
            yield response.follow(href, priority=0)

    def parse_book(self, response):
        book = response.as_html_parser().extract_model(BookDetailModel)

        return {**book, "category": response.meta["category"], "url": response.url}

    def book_failed(self, response):
        self.logger.error("could not fetch %s (%s)", response.url, response.status)

    async def on_close(self):
        self.logger.warning("finished: %s", self.stats)


async def main() -> None:
    # Class-level settings can be overridden per instance.
    spider = BooksSpider(concurrency=6, max_requests=30)
    books = await spider.collect()

    print(f"{len(books)} books, cheapest:")
    for book in sorted(books, key=lambda book: book["price"])[:3]:
        print(f"  £{book['price']:.2f}  {book['title']}  [{book['category']}]")

    print(f"status codes: {spider.stats.status_counts}")


if __name__ == "__main__":
    asyncio.run(main())

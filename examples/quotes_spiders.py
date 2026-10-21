"""
Exemplo de spiders do Xcrap rodando contra http://quotes.toscrape.com

    poetry run python examples/quotes_spiders.py
"""

import asyncio
import logging

from xcrap.extractor import HtmlBaseField, HtmlExtractionModel, css
from xcrap.spiders import MemoryPipeline, ModelSpider, Spider

logging.basicConfig(level=logging.WARNING)


class QuoteModel(HtmlExtractionModel):
    text = HtmlBaseField(query=css("span.text::text"))
    author = HtmlBaseField(query=css("small.author::text"))
    tags = HtmlBaseField(query=css("a.tag::text"), multiple=True)


class QuotesSpider(ModelSpider):
    """Declarativo: sem `parse`, só o modelo e as queries."""

    name = "quotes"
    start_urls = ["http://quotes.toscrape.com"]
    model = QuoteModel
    items_query = css("div.quote")
    follow_query = css("li.next a::attr(href)")
    concurrency = 4
    request_delay = 100


class AuthorsSpider(Spider):
    """Com callbacks: segue o link de cada autor e a paginação."""

    name = "authors"
    start_urls = ["http://quotes.toscrape.com"]
    max_requests = 15

    async def parse(self, response):
        parser = response.as_html_parser()

        for href in parser.extract_values(css("div.quote span a::attr(href)")):
            yield response.follow(href, callback="parse_author")

        for href in parser.extract_values(css("li.next a::attr(href)")):
            yield response.follow(href)

    def parse_author(self, response):
        parser = response.as_html_parser()

        return {
            "name": parser.extract_value(css("h3.author-title::text")),
            "born": parser.extract_value(css("span.author-born-date::text")),
        }


async def main() -> None:
    memory = MemoryPipeline()
    stats = await QuotesSpider(pipelines=[memory]).crawl()
    
    print(f"quotes: {len(memory.items)} itens em {stats.elapsed:.1f}s, status {stats.status_counts}")
    print(memory.items[0])

    authors = AuthorsSpider()
    items = await authors.collect()

    print(f"authors: {len(items)} itens, {authors.stats.requests_made} requests")
    print(items[:2])


if __name__ == "__main__":
    asyncio.run(main())

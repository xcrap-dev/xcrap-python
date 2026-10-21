"""
Item pipelines (quotes.toscrape.com): validate, clean, drop, deduplicate and export items.

Shows: ItemPipeline, DropItem, MemoryPipeline, JsonLinesPipeline, pydantic models as items.

    poetry run python examples/21_spider_pipelines.py

Writes quotes.jsonl to the current directory.
"""

from pydantic import BaseModel

from xcrap.extractor import HtmlBaseField, HtmlExtractionModel, css
from xcrap.spiders import DropItem, ItemPipeline, JsonLinesPipeline, MemoryPipeline, Spider


class QuoteModel(HtmlExtractionModel):
    text = HtmlBaseField(query=css("span.text::text"))
    author = HtmlBaseField(query=css("small.author::text"))
    tags = HtmlBaseField(query=css("a.tag::text"), multiple=True)


class Quote(BaseModel):
    text: str
    author: str
    tags: list[str]


class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com"]
    concurrency = 4
    request_delay = 200
    max_retries = 2  # handled by the HTTP client

    async def parse(self, response):
        parser = response.as_html_parser()

        for raw in parser.extract_models(QuoteModel, css("div.quote")):
            yield Quote(**raw)  # pydantic models are valid items

        for href in parser.extract_values(css("li.next a::attr(href)")):
            yield response.follow(href)


class StripQuotes(ItemPipeline):
    """Removes the typographic quotes around the text."""

    async def process_item(self, item, spider):
        return item.model_copy(update={"text": item.text.strip("“”")})


class DropLongQuotes(ItemPipeline):
    async def process_item(self, item, spider):
        if len(item.text) > 120:
            raise DropItem("too long")  # counted in stats.items_dropped

        return item


class Deduplicate(ItemPipeline):
    async def open_spider(self, spider):
        self.seen = set()

    async def process_item(self, item, spider):
        if item.text in self.seen:
            raise DropItem("duplicate")

        self.seen.add(item.text)

        return item


if __name__ == "__main__":
    memory = MemoryPipeline()
    spider = QuotesSpider(
        # Pipelines run in order; each receives the previous one's return value.
        pipelines=[StripQuotes(), DropLongQuotes(), Deduplicate(), memory, JsonLinesPipeline("quotes.jsonl")],
    )

    stats = spider.run()  # blocking helper around asyncio.run(spider.crawl())

    print(f"kept {stats.items_scraped}, dropped {stats.items_dropped}, {stats.requests_made} requests in {stats.elapsed:.1f}s")
    print(memory.items[0])

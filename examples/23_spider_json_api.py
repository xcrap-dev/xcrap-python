"""
A spider over a JSON API (quotes.toscrape.com/api/quotes) following the API's own pagination.

Shows: response.as_json_parser(), JsonExtractionModel items, building the next Request from the payload.

    poetry run python examples/23_spider_json_api.py
"""

import asyncio

from xcrap.extractor import JsonBaseField, JsonExtractionModel, jmes_path
from xcrap.spiders import Request, Spider


class QuoteModel(JsonExtractionModel):
    text = JsonBaseField(query=jmes_path("text"))
    author = JsonBaseField(query=jmes_path("author.name"))
    tags = JsonBaseField(query=jmes_path("tags"), multiple=True)


class QuotesApiSpider(Spider):
    name = "quotes-api"
    max_requests = 5  # keep the demo short

    async def start_requests(self):
        yield Request("https://quotes.toscrape.com/api/quotes?page=1", headers={"Accept": "application/json"})

    async def parse(self, response):
        parser = response.as_json_parser()

        for quote in parser.extract_models(QuoteModel, jmes_path("quotes")):
            yield quote

        if parser.extract_value(jmes_path("has_next")):
            page = parser.extract_value(jmes_path("page"))
            yield response.follow(f"/api/quotes?page={page + 1}")


async def main() -> None:
    spider = QuotesApiSpider()
    quotes = await spider.collect()

    print(f"{len(quotes)} quotes from {spider.stats.requests_made} API calls")
    print(quotes[-1])


if __name__ == "__main__":
    asyncio.run(main())

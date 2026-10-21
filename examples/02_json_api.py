"""
JSON extraction with JMESPath (quotes.toscrape.com API).

Shows: JsonExtractionModel, JsonParser, jmes_path, nested models, `response.as_json_parser()`.

    poetry run python examples/02_json_api.py
"""

import asyncio

from xcrap.clients import HttpxClient
from xcrap.extractor import JsonBaseField, JsonExtractionModel, JsonNestedField, jmes_path


class AuthorModel(JsonExtractionModel):
    name = JsonBaseField(query=jmes_path("name"))
    profile = JsonBaseField(query=jmes_path("goodreads_link"))


class QuoteModel(JsonExtractionModel):
    text = JsonBaseField(query=jmes_path("text"))
    tags = JsonBaseField(query=jmes_path("tags"), multiple=True)
    author = JsonNestedField(query=jmes_path("author"), model=AuthorModel)


class QuotesApiModel(JsonExtractionModel):
    page = JsonBaseField(query=jmes_path("page"))
    has_next = JsonBaseField(query=jmes_path("has_next"), default=False)
    quotes = JsonNestedField(query=jmes_path("quotes"), model=QuoteModel, multiple=True)


async def main() -> None:
    client = HttpxClient()
    response = await client.fetch(url="https://quotes.toscrape.com/api/quotes?page=1")
    parser = response.as_json_parser()

    # Whole document through a model...
    data = parser.extract_model(QuotesApiModel)
    print(f"page {data['page']}, has_next={data['has_next']}, {len(data['quotes'])} quotes")
    print(data["quotes"][0])

    # ...or ad-hoc queries (JMESPath projections, filters, slices).
    print(parser.extract_values(jmes_path("quotes[].author.name"), limit=3))
    print(parser.extract_value(jmes_path("quotes[?contains(tags, 'love')] | [0].text")))


if __name__ == "__main__":
    asyncio.run(main())

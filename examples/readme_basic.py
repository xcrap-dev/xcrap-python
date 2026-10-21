"""
Exemplo da seção "Como funciona" do README, rodando contra http://quotes.toscrape.com

    poetry run python examples/readme_basic.py
"""

import asyncio

from xcrap.clients import HttpxClient
from xcrap.extractor import HtmlBaseField, HtmlExtractionModel, HtmlNestedField, css


# 1. Defina seus modelos de forma declarativa
class AuthorModel(HtmlExtractionModel):
    name = HtmlBaseField(query=css("small.author::text"))
    link = HtmlBaseField(query=css("a::attr(href)"))


class QuoteModel(HtmlExtractionModel):
    text = HtmlBaseField(query=css("span.text::text"))
    # Modelos aninhados sem esforço!
    author = HtmlNestedField(model=AuthorModel)
    tags = HtmlBaseField(query=css("div.tags a.tag::text"), multiple=True)


class QuotesPageModel(HtmlExtractionModel):
    quotes = HtmlNestedField(query=css("div.quote"), model=QuoteModel, multiple=True)


async def main() -> None:
    client = HttpxClient()

    # 2. Busque a página
    response = await client.fetch(url="http://quotes.toscrape.com")

    # 3. Transforme em um parser e extraia os dados
    parser = response.as_html_parser()
    data = parser.extract_model(QuotesPageModel)

    for quote in data["quotes"][:3]:
        print(f"Quote: {quote['text']}")
        print(f"Author: {quote['author']['name']} ({quote['author']['link']})")
        print(f"Tags: {', '.join(quote['tags'])}\n")


if __name__ == "__main__":
    asyncio.run(main())

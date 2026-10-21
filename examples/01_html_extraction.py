"""
HTML extraction with declarative models (books.toscrape.com).

Shows: HttpxClient, HtmlExtractionModel, nested models, custom extractors, defaults, CSS and XPath.

    poetry run python examples/01_html_extraction.py
"""

import asyncio
import re

from xcrap.clients import HttpxClient
from xcrap.extractor import HtmlBaseField, HtmlExtractionModel, HtmlNestedField, css, xpath

RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


class BookModel(HtmlExtractionModel):
    title = HtmlBaseField(query=css("h3 a::attr(title)"))
    url = HtmlBaseField(query=css("h3 a::attr(href)"))
    # `extractor` receives the parsel Selector that matched the query, not a string.
    price = HtmlBaseField(
        query=css("p.price_color"),
        extractor=lambda el: float(re.search(r"\d+\.\d+", el.get())[0]),
    )
    rating = HtmlBaseField(
        query=css("p.star-rating"),
        extractor=lambda el: RATINGS[el.attrib["class"].split()[-1]],
    )
    # XPath works too, and `default` is used when nothing matches.
    in_stock = HtmlBaseField(
        query=xpath("normalize-space(.//p[contains(@class, 'availability')])"),
        default="unknown",
    )


class CategoryModel(HtmlExtractionModel):
    name = HtmlBaseField(query=css("a::text"))


class CataloguePageModel(HtmlExtractionModel):
    # A nested model without a query receives the current element.
    heading = HtmlBaseField(query=css("div.page-header h1::text"))
    categories = HtmlNestedField(query=css("div.side_categories ul ul li"), model=CategoryModel, multiple=True, limit=5)
    books = HtmlNestedField(query=css("article.product_pod"), model=BookModel, multiple=True)


async def main() -> None:
    client = HttpxClient()
    response = await client.fetch(url="https://books.toscrape.com/")

    page = response.as_html_parser().extract_model(CataloguePageModel)

    print(f"{page['heading'].strip()} - first categories: {[c['name'].strip() for c in page['categories']]}")

    for book in page["books"][:5]:
        print(f"{book['title']!r}: £{book['price']} ({book['rating']}★, {book['in_stock']})")


if __name__ == "__main__":
    asyncio.run(main())

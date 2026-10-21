"""
JSON embedded in an HTML <script> tag (quotes.toscrape.com/js/).

The page has no quotes in its markup: they live in a `var data = [...]` JavaScript literal, which is
valid JSON. Pull the script text out with the HTML parser, cut the literal, hand it to JsonParser.

    poetry run python examples/04_json_inside_html.py
"""

import asyncio
import re

from xcrap.clients import HttpxClient
from xcrap.extractor import JsonBaseField, JsonExtractionModel, JsonParser, css, jmes_path


class QuoteModel(JsonExtractionModel):
    text = JsonBaseField(query=jmes_path("text"))
    author = JsonBaseField(query=jmes_path("author.name"))
    tags = JsonBaseField(query=jmes_path("tags"), multiple=True)


async def main() -> None:
    client = HttpxClient()
    response = await client.fetch(url="https://quotes.toscrape.com/js/")
    html = response.as_html_parser()

    print("quotes in the markup:", len(html.extract_values(css("div.quote"))))

    # HTML -> script text -> JSON
    scripts = html.extract_values(css("script:not([src])::text"))
    literal = next(m.group(1) for script in scripts if (m := re.search(r"var data = (\[.*?\]);", script, re.S)))
    parser = JsonParser(literal)

    for quote in parser.extract_models(QuoteModel, jmes_path("@"), limit=3):
        print(f"{quote['author']}: {quote['text']} {quote['tags']}")


if __name__ == "__main__":
    asyncio.run(main())

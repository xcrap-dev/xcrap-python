"""
Markdown extraction (a raw README from GitHub).

Markdown is rendered to HTML and queried with the same CSS/XPath API as any HTML document.

Shows: MarkdownParser, MarkdownExtractionModel, `response.as_markdown_parser()`.

    poetry run python examples/03_markdown.py
"""

import asyncio

from xcrap.clients import HttpxClient
from xcrap.extractor import HtmlBaseField, MarkdownExtractionModel, css


class ReadmeModel(MarkdownExtractionModel):
    title = HtmlBaseField(query=css("h1::text"))
    sections = HtmlBaseField(query=css("h2::text"), multiple=True)
    code_blocks = HtmlBaseField(query=css("pre code::text"), multiple=True, limit=2)
    links = HtmlBaseField(query=css("p a::attr(href)"), multiple=True, limit=5)


async def main() -> None:
    client = HttpxClient()
    response = await client.fetch(url="https://raw.githubusercontent.com/psf/requests/main/README.md")

    # Parser flavour: queries on demand.
    parser = response.as_markdown_parser()
    print("title:", parser.extract_value(css("h1::text")))

    # Model flavour: a whole structure at once (the model accepts the raw Markdown string).
    readme = ReadmeModel().extract(response.text)
    print("sections:", readme["sections"])
    print("first links:", readme["links"])
    print("first code block:\n", readme["code_blocks"][0])


if __name__ == "__main__":
    asyncio.run(main())

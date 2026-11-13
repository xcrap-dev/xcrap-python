"""
XML feeds: a GitHub releases Atom feed.

Shows XmlParser and XmlExtractionModel, the two ways of handling XML namespaces (registered prefixes
and remove_namespaces), and HTML living inside an XML element (the release notes).

    poetry run python examples/07_xml_feeds.py
"""

import asyncio

from xcrap.clients import HttpxClient
from xcrap.extractor import (
    HtmlBaseField,
    HtmlExtractionModel,
    HtmlParser,
    XmlBaseField,
    XmlExtractionModel,
    XmlNestedField,
    css,
    xpath,
)

ATOM = {"atom": "http://www.w3.org/2005/Atom"}


class NotesModel(HtmlExtractionModel):
    headings = HtmlBaseField(query=css("h2::text, h3::text"), multiple=True)
    links = HtmlBaseField(query=css("a::attr(href)"), multiple=True, limit=3)


class EntryModel(XmlExtractionModel):
    namespaces = ATOM

    title = XmlBaseField(query=xpath("normalize-space(atom:title)"))
    updated = XmlBaseField(query=xpath("atom:updated/text()"))
    url = XmlBaseField(query=xpath("atom:link[@rel='alternate']/@href"))
    # <content type="html"> holds escaped HTML: its text is an HTML document for a nested HTML model
    notes = XmlNestedField(query=xpath("atom:content"), model=NotesModel, extractor=lambda el: el.xpath("string(.)").get())


class FeedModel(XmlExtractionModel):
    namespaces = ATOM

    title = XmlBaseField(query=xpath("/atom:feed/atom:title/text()"))
    entries = XmlNestedField(query=xpath("//atom:entry"), model=EntryModel, multiple=True, limit=3)


async def main() -> None:
    client = HttpxClient()
    response = await client.fetch(url="https://github.com/psf/requests/releases.atom", max_retries=2, retry_delay=1000)

    if not response.is_success():
        raise SystemExit(f"request failed: {response.status}")

    # 1. A declarative model with registered namespace prefixes
    feed = response.as_xml_parser().extract_model(FeedModel)
    print("feed:", feed["title"])

    for entry in feed["entries"]:
        print(f"- {entry['title']} ({entry['updated']}) {entry['url']}")
        print("  headings:", entry["notes"]["headings"])

    # 2. Ad-hoc queries after stripping namespaces: plain names and CSS just work
    parser = response.as_xml_parser(remove_namespaces=True)
    print("all release titles:", [title.strip() for title in parser.extract_values(css("entry > title::text"))])

    # 3. The same HTML-inside-XML hop done by hand
    first_notes = parser.extract_value(xpath("string(//entry[1]/content)"))
    print("first release links:", HtmlParser(first_notes).extract_values(css("a::attr(href)"))[:3])


if __name__ == "__main__":
    asyncio.run(main())

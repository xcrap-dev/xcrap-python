import pytest
from parsel import Selector

from xcrap.extractor import (
    HtmlBaseField,
    HtmlExtractionModel,
    XmlBaseField,
    XmlExtractionModel,
    XmlNestedField,
    XmlParser,
    create_xml_selector,
    css,
    xpath,
)

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>Example Blog</title>
    <item>
      <title>First &amp; best</title>
      <link>https://blog.test/1</link>
      <category>news</category>
      <category>python</category>
      <media:content url="https://blog.test/1.jpg"/>
      <description><![CDATA[<p>Hello <b>world</b></p>]]></description>
    </item>
    <item>
      <title>Second</title>
      <link>https://blog.test/2</link>
    </item>
  </channel>
</rss>
"""

ATOM = """<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Feed</title>
  <entry><title>Entry A</title><link rel="alternate" href="https://a.test/a"/></entry>
  <entry><title>Entry B</title><link rel="alternate" href="https://a.test/b"/></entry>
</feed>"""

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://site.test/</loc><lastmod>2024-01-01</lastmod></url>
  <url><loc>https://site.test/about</loc></url>
</urlset>"""

MEDIA = {"media": "http://search.yahoo.com/mrss/"}


class ItemModel(XmlExtractionModel):
    namespaces = MEDIA

    title = XmlBaseField(query=xpath("title/text()"))
    url = XmlBaseField(query=css("link::text"))
    categories = XmlBaseField(query=xpath("category/text()"), multiple=True)
    image = XmlBaseField(query=xpath("media:content/@url"))


class FeedModel(XmlExtractionModel):
    title = XmlBaseField(query=xpath("/rss/channel/title/text()"))
    items = XmlNestedField(query=xpath("//item"), model=ItemModel, multiple=True)


# --- parser ------------------------------------------------------------------------------------


def test_xml_parser_extract_value_and_values() -> None:
    parser = XmlParser(RSS)

    assert parser.extract_value(xpath("//channel/title/text()")) == "Example Blog"
    assert parser.extract_value(css("channel > title::text")) == "Example Blog"
    assert parser.extract_value(xpath("//missing/text()"), default="n/a") == "n/a"
    assert parser.extract_values(xpath("//item/title/text()")) == ["First & best", "Second"]
    assert parser.extract_values(xpath("//item/link/text()"), limit=1) == ["https://blog.test/1"]
    assert parser.root is parser.selector
    assert parser.content == RSS


def test_xml_parser_accepts_bytes() -> None:
    parser = XmlParser(RSS.encode("utf-8"))

    assert parser.extract_value(xpath("//channel/title/text()")) == "Example Blog"


def test_xml_parser_reads_cdata_as_text() -> None:
    parser = XmlParser(RSS)

    assert parser.extract_value(xpath("//item[1]/description/text()")) == "<p>Hello <b>world</b></p>"


def test_xml_parser_extract_model_and_models() -> None:
    parser = XmlParser(RSS, namespaces=MEDIA)

    feed = parser.extract_model(FeedModel)
    first = parser.extract_model(ItemModel, xpath("//item"))
    items = parser.extract_models(ItemModel, xpath("//item"), limit=1)

    assert feed == {
        "title": "Example Blog",
        "items": [
            {
                "title": "First & best",
                "url": "https://blog.test/1",
                "categories": ["news", "python"],
                "image": "https://blog.test/1.jpg",
            },
            {"title": "Second", "url": "https://blog.test/2", "categories": [], "image": None},
        ],
    }
    assert first == feed["items"][0]
    assert items == [feed["items"][0]]


def test_xml_parser_extract_model_accepts_instances_and_missing_queries() -> None:
    parser = XmlParser(RSS)
    model = XmlExtractionModel(shape={"title": XmlBaseField(query=xpath("title/text()"))})

    assert parser.extract_model(model, xpath("//item")) == {"title": "First & best"}
    assert parser.extract_models(model, xpath("//item")) == [{"title": "First & best"}, {"title": "Second"}]
    assert parser.extract_model(model, xpath("//missing")) is None


def test_xml_parser_namespaces() -> None:
    parser = XmlParser(ATOM, namespaces={"atom": "http://www.w3.org/2005/Atom"})

    assert parser.extract_values(xpath("//atom:entry/atom:title/text()")) == ["Entry A", "Entry B"]
    assert parser.extract_values(xpath("//entry")) == []


def test_xml_parser_remove_namespaces() -> None:
    parser = XmlParser(SITEMAP, remove_namespaces=True)

    assert parser.extract_values(xpath("//url/loc/text()")) == ["https://site.test/", "https://site.test/about"]
    assert parser.extract_values(css("url loc::text")) == ["https://site.test/", "https://site.test/about"]


def test_xml_parser_local_name_without_namespace_setup() -> None:
    parser = XmlParser(SITEMAP)

    assert parser.extract_values(xpath("//*[local-name()='loc']/text()")) == ["https://site.test/", "https://site.test/about"]


def test_xml_parser_load_file(tmp_path) -> None:
    path = tmp_path / "feed.xml"
    path.write_text(RSS, encoding="utf-8")

    parser = XmlParser.load_file(str(path))

    assert isinstance(parser, XmlParser)
    assert parser.extract_value(xpath("//channel/title/text()")) == "Example Blog"


def test_xml_parser_does_not_resolve_entities() -> None:
    xxe = '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY secret SYSTEM "file:///etc/passwd">]><r>&secret;</r>'

    parser = XmlParser(xxe)

    assert "root:" not in (parser.extract_value(xpath("string(/r)")) or "")


# --- model -------------------------------------------------------------------------------------


def test_xml_model_extracts_from_string_and_selector() -> None:
    assert FeedModel().extract(RSS)["title"] == "Example Blog"
    assert FeedModel().extract(Selector(text=RSS, type="xml"))["title"] == "Example Blog"
    assert FeedModel().extract(RSS.encode())["title"] == "Example Blog"


def test_xml_model_registers_namespaces_on_given_selectors() -> None:
    item = Selector(text=RSS, type="xml").xpath("//item")[0]

    assert ItemModel().extract(item)["image"] == "https://blog.test/1.jpg"


def test_xml_model_namespaces_from_constructor_and_inheritance() -> None:
    class AtomModel(XmlExtractionModel):
        namespaces = {"atom": "http://www.w3.org/2005/Atom"}
        title = XmlBaseField(query=xpath("/atom:feed/atom:title/text()"))

    class AtomWithEntries(AtomModel):
        entries = XmlBaseField(query=xpath("//atom:entry/atom:title/text()"), multiple=True)

    by_constructor = XmlExtractionModel(
        shape={"title": XmlBaseField(query=xpath("/a:feed/a:title/text()"))},
        namespaces={"a": "http://www.w3.org/2005/Atom"},
    )

    assert AtomWithEntries().extract(ATOM) == {"title": "Atom Feed", "entries": ["Entry A", "Entry B"]}
    assert by_constructor.extract(ATOM) == {"title": "Atom Feed"}
    assert XmlExtractionModel().namespaces == {}


def test_xml_model_remove_namespaces_class_attribute_and_override() -> None:
    class SitemapModel(XmlExtractionModel):
        remove_namespaces = True
        urls = XmlBaseField(query=xpath("//url/loc/text()"), multiple=True)

    assert SitemapModel().extract(SITEMAP) == {"urls": ["https://site.test/", "https://site.test/about"]}
    assert SitemapModel(remove_namespaces=False).extract(SITEMAP) == {"urls": []}


def test_xml_base_field_defaults_limits_and_extractors() -> None:
    class Model(XmlExtractionModel):
        missing = XmlBaseField(query=xpath("//missing/text()"), default="none")
        missing_list = XmlBaseField(query=xpath("//missing/text()"), multiple=True)
        missing_list_default = XmlBaseField(query=xpath("//missing/text()"), multiple=True, default=["x"])
        first_link = XmlBaseField(query=xpath("//item/link/text()"), multiple=True, limit=1)
        link_count = XmlBaseField(query=xpath("//item"), multiple=True, extractor=lambda el: el.xpath("name()").get())
        version = XmlBaseField(query=xpath("/rss"), extractor=lambda el: el.attrib["version"])
        channel = XmlBaseField(query=xpath("//channel/title"))

    assert Model().extract(RSS) == {
        "missing": "none",
        "missing_list": [],
        "missing_list_default": ["x"],
        "first_link": ["https://blog.test/1"],
        "link_count": ["item", "item"],
        "version": "2.0",
        "channel": '<title xmlns:media="http://search.yahoo.com/mrss/">Example Blog</title>',  # in-scope namespaces are serialized
    }


def test_xml_nested_field_variants() -> None:
    title_model = XmlExtractionModel(shape={"title": XmlBaseField(query=xpath("title/text()"))})

    class Model(XmlExtractionModel):
        channel = XmlNestedField(model=title_model, query=xpath("//channel"))
        grouped = XmlNestedField(model=title_model)  # no query: the current element
        first_item = XmlNestedField(model=title_model, query=xpath("//item"))
        two = XmlNestedField(model=title_model, query=xpath("//item"), multiple=True, limit=1)
        missing = XmlNestedField(model=title_model, query=xpath("//missing"), default={"title": None})
        missing_list = XmlNestedField(model=title_model, query=xpath("//missing"), multiple=True)
        missing_list_default = XmlNestedField(model=title_model, query=xpath("//missing"), multiple=True, default=[1])

    assert Model().extract(RSS) == {
        "channel": {"title": "Example Blog"},
        "grouped": {"title": None},
        "first_item": {"title": "First & best"},
        "two": [{"title": "First & best"}],
        "missing": {"title": None},
        "missing_list": [],
        "missing_list_default": [1],
    }


def test_xml_nested_field_with_extractor_chains_formats() -> None:
    class DescriptionModel(HtmlExtractionModel):
        bold = HtmlBaseField(query=css("b::text"))

    class Model(XmlExtractionModel):
        description = XmlNestedField(
            query=xpath("//item[1]/description"),
            model=DescriptionModel,
            extractor=lambda el: el.xpath("text()").get(),
        )

    assert Model().extract(RSS) == {"description": {"bold": "world"}}


def test_xml_nested_multiple_requires_query() -> None:
    class Model(XmlExtractionModel):
        items = XmlNestedField(model=XmlExtractionModel, multiple=True)

    with pytest.raises(ValueError, match="Query is required"):
        Model().extract(RSS)


def test_xml_absolute_xpath_in_nested_models_searches_the_whole_document() -> None:
    class Absolute(XmlExtractionModel):
        title = XmlBaseField(query=xpath("//title/text()"))

    class Relative(XmlExtractionModel):
        title = XmlBaseField(query=xpath(".//title/text()"))

    absolute = XmlParser(RSS).extract_models(Absolute, xpath("//item"))
    relative = XmlParser(RSS).extract_models(Relative, xpath("//item"))

    assert absolute == [{"title": "Example Blog"}, {"title": "Example Blog"}]
    assert relative == [{"title": "First & best"}, {"title": "Second"}]


def test_create_xml_selector() -> None:
    selector = create_xml_selector(ATOM, namespaces={"a": "http://www.w3.org/2005/Atom"})

    assert selector.type == "xml"
    assert selector.xpath("//a:entry/a:title/text()").getall() == ["Entry A", "Entry B"]
    assert create_xml_selector(ATOM, remove_namespaces=True).xpath("//entry/title/text()").getall() == ["Entry A", "Entry B"]

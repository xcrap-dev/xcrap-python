# XML (RSS, Atom, sitemaps)

```python
from xcrap.extractor import XmlBaseField, XmlExtractionModel, XmlNestedField, XmlParser, css, xpath
```

`XmlParser` and `XmlExtractionModel` mirror the HTML API: same parser methods, same field options (`query`, `default`, `multiple`, `limit`, `extractor`, nested `model`), CSS and XPath queries. They use lxml's XML parser: names are case-sensitive, there is no HTML repair, and external entities are never resolved.

## RSS

```python
class ItemModel(XmlExtractionModel):
    title = XmlBaseField(query=xpath("title/text()"))
    url = XmlBaseField(query=xpath("link/text()"))
    published = XmlBaseField(query=xpath("pubDate/text()"))
    categories = XmlBaseField(query=xpath("category/text()"), multiple=True)


class FeedModel(XmlExtractionModel):
    title = XmlBaseField(query=xpath("/rss/channel/title/text()"))
    items = XmlNestedField(query=xpath("//item"), model=ItemModel, multiple=True, limit=20)


parser = XmlParser(feed_xml)          # str or bytes; or response.as_xml_parser(); XmlParser.load_file("feed.xml")
feed = parser.extract_model(FeedModel)
items = parser.extract_models(ItemModel, xpath("//item"))
titles = parser.extract_values(xpath("//item/title/text()"))
```

- Inside `ItemModel`, use **relative** paths (`title/text()`, `.//title/text()`). `//title` searches the whole document and would return the channel title for every item.
- `XmlParser.extract_model()`/`extract_models()` accept a model class **or** instance; `extract_model(model, query)` returns `None` when the query matches nothing.
- Elements selected without `text()` come back serialized as XML, including the namespace declarations in scope. Select `text()`, `string(.)` or `normalize-space(.)` for text.
- CDATA is read as text, so HTML in `<description>` or `<content:encoded>` can go to `HtmlParser`, or to a nested `HtmlExtractionModel` through `extractor=lambda el: el.xpath("string(.)").get()`.

## Namespaces

Atom (`http://www.w3.org/2005/Atom`), sitemaps (`http://www.sitemaps.org/schemas/sitemap/0.9`) and media RSS put elements in namespaces, and an unprefixed XPath does not match namespaced elements. Prefixes declared in the document are **not** registered automatically. Pick one approach:

### 1. Register prefixes

```python
ATOM = {"atom": "http://www.w3.org/2005/Atom"}

parser = XmlParser(atom_xml, namespaces=ATOM)
parser.extract_values(xpath("//atom:entry/atom:title/text()"))


class EntryModel(XmlExtractionModel):
    namespaces = ATOM                                   # class attribute (inherited and merged)
    title = XmlBaseField(query=xpath("normalize-space(atom:title)"))
    url = XmlBaseField(query=xpath("atom:link[@rel='alternate']/@href"))


class MediaItemModel(XmlExtractionModel):
    namespaces = {"media": "http://search.yahoo.com/mrss/"}
    image = XmlBaseField(query=xpath("media:content/@url"))


XmlExtractionModel(shape={...}, namespaces=ATOM)        # or per instance
```

A model registers its namespaces on the selector it receives, so each nested model can declare its own.

### 2. Strip namespaces

Simplest for sitemaps and Atom, and it makes CSS selectors work:

```python
XmlParser(sitemap_xml, remove_namespaces=True).extract_values(css("url loc::text"))
response.as_xml_parser(remove_namespaces=True)


class SitemapModel(XmlExtractionModel):
    remove_namespaces = True
    urls = XmlBaseField(query=xpath("//url/loc/text()"), multiple=True)
    modified = XmlBaseField(query=xpath("//url/lastmod/text()"), multiple=True)
```

`remove_namespaces` only applies when the model parses the document itself (string/bytes). A nested model works on whatever its parent parsed.

### 3. Match the local name

No setup, works anywhere:

```python
XmlParser(sitemap_xml).extract_values(xpath("//*[local-name()='loc']/text()"))
```

## Sitemap index → sitemaps → URLs

```python
async def sitemap_urls(client, index_url: str) -> list[str]:
    index = (await client.fetch(url=index_url)).as_xml_parser(remove_namespaces=True)
    sitemap_locations = index.extract_values(xpath("//sitemap/loc/text()"))

    responses = await client.fetch_many([{"url": url} for url in sitemap_locations], request_delay=200, concurrency=2)

    return [
        loc
        for response in responses
        if response.is_success()
        for loc in response.as_xml_parser(remove_namespaces=True).extract_values(xpath("//url/loc/text()"))
    ]
```

## Factories

`create_extraction_model` builds XML models too: map a type to `XmlExtractionModel` in `allowed_models` and add `"namespaces"` / `"remove_namespaces"` next to `"type"` in the config.

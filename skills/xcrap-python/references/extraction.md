# Extraction

```python
from xcrap.extractor import (
    HtmlBaseField, HtmlExtractionModel, HtmlNestedField, HtmlParser,
    JsonBaseField, JsonExtractionModel, JsonNestedField, JsonParser,
    MarkdownExtractionModel, MarkdownParser,
    css, jmes_path, xpath,
)
```

Two levels, same queries:

- **Parsers** answer ad-hoc questions: *the text of this selector*.
- **Models** describe a whole structure once and return plain `dict`s/`list`s.

## Queries

| Helper | Language | Formats |
| --- | --- | --- |
| `css("a.next::attr(href)")` | CSS + parsel pseudo-elements `::text`, `::attr(name)`, `:contains()` | HTML, Markdown, XML |
| `xpath("//h1/text()")` | XPath 1.0 (`normalize-space()`, `string()`, axes) | HTML, Markdown, XML |
| `jmes_path("items[].name")` | [JMESPath](https://jmespath.org) | JSON |

Without `::text`/`::attr()`/`text()` a query returns the element's **HTML**. Prefer CSS; use XPath for text matching (`//dt[text()='Brand']/following-sibling::dd[1]/text()`), axes and functions.

## HtmlParser

```python
parser = HtmlParser(html)                      # or response.as_html_parser(), HtmlParser.load_file("page.html")

parser.extract_value(css("h1::text"))                       # first match or None
parser.extract_value(css(".promo::text"), default="n/a")
parser.extract_values(css("li::text"), limit=10)            # every match
parser.extract_model(PageModel)                             # whole document (pass the model CLASS)
parser.extract_model(ItemModel, css("li"))                  # first match (IndexError if nothing matches)
parser.extract_models(ItemModel, css("li"), limit=20)       # one dict per match
parser.selector                                             # the parsel Selector (alias: parser.root)
```

## HtmlExtractionModel

```python
class QuoteModel(HtmlExtractionModel):
    text = HtmlBaseField(query=css("span.text::text"))
    tags = HtmlBaseField(query=css("a.tag::text"), multiple=True)
    rating = HtmlBaseField(query=css(".rating::text"), default="unrated")
    author_url = HtmlBaseField(query=css("a[href*='author']::attr(href)"))
```

`QuoteModel().extract(html_or_selector)` → `{"text": ..., "tags": [...], "rating": ..., "author_url": ...}`.

### HtmlBaseField

| Option | Default | Meaning |
| --- | --- | --- |
| `query` | required | Where to look |
| `default` | `None` | Returned when nothing matches (`[]` when `multiple`) |
| `multiple` | `False` | List of every match |
| `limit` | `None` | Max items with `multiple` |
| `extractor` | `None` | Function applied to each matched **parsel `Selector`** |

Missing elements return `default` (`None`) instead of raising, so *required* fields must be enforced in the validation layer (pydantic).

```python
rating = HtmlBaseField(query=css("p.star-rating"), extractor=lambda el: el.attrib["class"].split()[-1])
sku = HtmlBaseField(query=css(".product"), extractor=lambda el: el.attrib.get("data-sku"))
```

Keep extractors about *reading* the element (attributes, sub-queries). Converting prices, dates and URLs belongs in pydantic.

### HtmlNestedField

| Option | Meaning |
| --- | --- |
| `model` | Model class or instance |
| `query` | Which element(s). **Omit it** to pass the current element through (groups fields) |
| `multiple` / `limit` / `default` | As above; `multiple=True` requires `query` |
| `extractor` | Transform the matched element before the nested model sees it (e.g. take a `<script>`'s text) |

```python
class PageModel(HtmlExtractionModel):
    category = HtmlBaseField(query=css("h1::text"))
    quotes = HtmlNestedField(query=css("div.quote"), model=QuoteModel, multiple=True)
    author = HtmlNestedField(model=AuthorModel)  # no query: same element
```

Nested **CSS** queries are relative to the matched element. Nested **XPath** starting with `//` searches the whole document:

```python
name = HtmlBaseField(query=xpath("//span/text()"))   # wrong in a nested model: always the first span of the page
name = HtmlBaseField(query=xpath(".//span/text()"))  # right: inside this element
```

### Inheritance and shapes

```python
class DetailedQuoteModel(QuoteModel):                  # inherits and can override fields
    year = HtmlBaseField(query=css(".year::text"))

model = HtmlExtractionModel(shape={"title": HtmlBaseField(query=css("h1::text"))})  # no class; what factories use
```

Instances work for nested fields and `model.extract(...)`, but `parser.extract_model()` / `extract_models()` of `HtmlParser` and `JsonParser` expect a **class** (they call `model()`); with an instance call `instance.extract(parser.selector)` directly.

## JSON

```python
class QuoteModel(JsonExtractionModel):
    text = JsonBaseField(query=jmes_path("text"))
    tags = JsonBaseField(query=jmes_path("tags"), multiple=True)
    author = JsonNestedField(query=jmes_path("author"), model=AuthorModel)


class PageModel(JsonExtractionModel):
    has_next = JsonBaseField(query=jmes_path("has_next"), default=False)
    quotes = JsonNestedField(query=jmes_path("quotes"), model=QuoteModel, multiple=True)


parser = JsonParser(text)                      # or response.as_json_parser()
parser.extract_model(PageModel)
parser.extract_models(QuoteModel, jmes_path("quotes"), limit=5)
parser.extract_value(jmes_path("quotes[0].author.name"))
parser.extract_values(jmes_path("quotes[].author.name"))
```

- No `extractor` on JSON fields: JMESPath already projects, filters and renames (`items[].{id: id, name: attributes.title}`).
- `default` applies when the query yields `null`.
- Quote keys with dots: `jmes_path('payload."a.b".items')`.
- `extract()` accepts a JSON string or an already-parsed `dict`/`list`.

## Markdown

Rendered to HTML (`extra`, `tables`, `fenced_code`, `toc`, `sane_lists`) and queried as HTML:

```python
parser = MarkdownParser(markdown_text)         # or response.as_markdown_parser()
parser.extract_values(css("h2::text"))
parser.extract_values(css("pre code::text"))


class ReadmeModel(MarkdownExtractionModel):    # HTML fields, Markdown input
    title = HtmlBaseField(query=css("h1::text"))
    sections = HtmlBaseField(query=css("h2::text"), multiple=True)
```

## XML

See [xml.md](xml.md).

## Composing formats

Every parser takes a string: extract the inner document with the outer parser and feed it to the next one.

```python
# JSON inside HTML
script = response.as_html_parser().extract_value(css("script#__NEXT_DATA__::text"))
items = JsonParser(script).extract_values(jmes_path("props.pageProps.items[].title"))

# Markdown inside JSON
notes = MarkdownParser(response.as_json_parser().extract_value(jmes_path("body")))

# JavaScript literal inside a script
import re
literal = re.search(r"var data = (\[.*?\]);", script_text, re.S).group(1)
JsonParser(literal)
```

Or inside a model, with a nested field whose `extractor` returns the inner document:

```python
class PageModel(HtmlExtractionModel):
    product = HtmlNestedField(
        query=css("script#__NEXT_DATA__"),
        model=NextDataModel,                          # a JsonExtractionModel
        extractor=lambda el: el.css("::text").get(),
    )
```

Keep each hop small and named: embedded payloads change shape without notice.

## OCR

With `xcrap[ocr]` and Tesseract installed:

```python
from xcrap.ocr import extract_image_text, image_text_extractor

code = HtmlBaseField(query=css("img.code"), extractor=image_text_extractor(lang="eng"))  # reads src as a LOCAL path
extract_image_text(image_bytes)                                                        # path, bytes or PIL.Image
```

Download remote images with a client first and pass the bytes to `extract_image_text()`.

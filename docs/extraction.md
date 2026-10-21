# Extraction

Extraction turns a document (HTML, JSON, Markdown) into plain Python data. There are two levels:

- **Parsers** answer ad-hoc questions: *what is the text of this selector?*
- **Models** describe a whole structure once: *a page has a title and a list of quotes, each with an author…*

Both use the same **queries**.

## Queries

Three tiny helpers build a `QueryConfig` (`{"type": ..., "value": ...}`):

| Helper | Language | Used with |
| --- | --- | --- |
| `css("div.quote a::attr(href)")` | CSS selectors with `::text` / `::attr(name)` pseudo-elements | HTML, Markdown |
| `xpath("//h1/text()")` | XPath 1.0 | HTML, Markdown |
| `jmes_path("quotes[].author.name")` | [JMESPath](https://jmespath.org) | JSON |

```python
from xcrap.extractor import css, jmes_path, xpath
```

CSS/XPath run on [parsel](https://parsel.readthedocs.io) selectors, so everything parsel supports works: `::text`, `::attr()`, `:contains('text')`, `:nth-child()`, and XPath functions such as `normalize-space()`, which returns clean text.

## HTML

### Parser

```python
from xcrap.extractor import HtmlParser

parser = HtmlParser("<ul><li>a</li><li>b</li></ul>")     # or response.as_html_parser()

parser.extract_value(css("li::text"))                      # 'a'      first match, or default
parser.extract_value(css("p::text"), default="n/a")        # 'n/a'
parser.extract_values(css("li::text"))                     # ['a', 'b']
parser.extract_values(css("li::text"), limit=1)            # ['a']

parser.extract_model(PageModel)                            # whole document through a model
parser.extract_model(ItemModel, css("li"))                 # first match through a model
parser.extract_models(ItemModel, css("li"), limit=10)      # every match through a model -> list
```

`parser.selector` (alias `parser.root`) is the underlying parsel `Selector` if you need it. Any parser can be built from a file with `HtmlParser.load_file("page.html")`.

### Models

A model is a class whose attributes are *fields*:

```python
from xcrap.extractor import HtmlBaseField, HtmlExtractionModel, HtmlNestedField, css

class QuoteModel(HtmlExtractionModel):
    text = HtmlBaseField(query=css("span.text::text"))
    tags = HtmlBaseField(query=css("a.tag::text"), multiple=True)
    rating = HtmlBaseField(query=css(".rating::text"), default="unrated")
```

Calling `QuoteModel().extract(selector_or_html)` (or `parser.extract_model(QuoteModel)`) returns `{"text": ..., "tags": [...], "rating": ...}`.

#### `HtmlBaseField`

| Option | Default | Meaning |
| --- | --- | --- |
| `query` | required | Where to look |
| `default` | `None` | Returned when nothing matches (`[]` if `multiple`) |
| `multiple` | `False` | Return a list of every match instead of the first |
| `limit` | `None` | With `multiple`, keep only the first N |
| `extractor` | `None` | Function applied to each matching **`Selector`** to produce the value |

An `extractor` receives the parsel `Selector`, not a string — call `.get()`, `.attrib`, `.css()` on it:

```python
price = HtmlBaseField(
    query=css("p.price"),
    extractor=lambda el: float(el.css("::text").get().replace("$", "")),
)
rating = HtmlBaseField(query=css("p.star-rating"), extractor=lambda el: el.attrib["class"].split()[-1])
```

#### `HtmlNestedField`

Applies another model to an element (or to each element):

| Option | Meaning |
| --- | --- |
| `model` | A model class or instance |
| `query` | Which element(s). **Omit it** to pass the current element straight through — handy to group fields |
| `multiple` / `limit` / `default` | As above. `multiple=True` requires a `query` |
| `extractor` | Transform the matched element before the nested model sees it |

```python
class PageModel(HtmlExtractionModel):
    quotes = HtmlNestedField(query=css("div.quote"), model=QuoteModel, multiple=True)
    footer = HtmlNestedField(query=css("footer"), model=FooterModel)     # single nested object
```

Nested queries are relative to the matched element, so `css("span.text::text")` inside `QuoteModel` only sees that quote.

#### Inheritance and dynamic shapes

Fields are inherited and can be overridden:

```python
class DetailedQuoteModel(QuoteModel):
    year = HtmlBaseField(query=css(".year::text"))       # keeps text, tags, rating
```

You can also build a model without a class by passing a `shape`, which is exactly what the [factories](factories.md) do:

```python
model = HtmlExtractionModel(shape={"title": HtmlBaseField(query=css("h1::text"))})
```

## JSON

JSON uses the same ideas with JMESPath queries.

```python
from xcrap.extractor import JsonBaseField, JsonExtractionModel, JsonNestedField, JsonParser, jmes_path

class AuthorModel(JsonExtractionModel):
    name = JsonBaseField(query=jmes_path("name"))

class QuoteModel(JsonExtractionModel):
    text = JsonBaseField(query=jmes_path("text"))
    tags = JsonBaseField(query=jmes_path("tags"), multiple=True)
    author = JsonNestedField(query=jmes_path("author"), model=AuthorModel)

class PageModel(JsonExtractionModel):
    has_next = JsonBaseField(query=jmes_path("has_next"), default=False)
    quotes = JsonNestedField(query=jmes_path("quotes"), model=QuoteModel, multiple=True)

parser = JsonParser(text)                       # or response.as_json_parser()
parser.extract_model(PageModel)                 # model over the whole document
parser.extract_models(QuoteModel, jmes_path("quotes"), limit=5)
parser.extract_value(jmes_path("quotes[0].author.name"))
parser.extract_values(jmes_path("quotes[].author.name"))
```

Differences from HTML: fields have no `extractor` (JMESPath already transforms: projections, filters, functions), `default` applies when the query yields `null`, and keys containing dots must be quoted — `jmes_path('payload."a.b".items')`. A model's `extract()` accepts a JSON string *or* already-parsed `dict`/`list`. Runnable: [`examples/02_json_api.py`](../examples/02_json_api.py).

## Markdown

Markdown is rendered to HTML (extensions: `extra`, `tables`, `fenced_code`, `toc`, `sane_lists`) and then queried with CSS/XPath, so headings, links, tables and code blocks are all selectable.

```python
from xcrap.extractor import HtmlBaseField, MarkdownExtractionModel, MarkdownParser, css

parser = MarkdownParser(markdown_text)                 # or response.as_markdown_parser()
parser.extract_value(css("h1::text"))
parser.extract_values(css("h2::text"))
parser.extract_values(css("pre code::text"))
parser.extract_values(css("table tr td::text"))

class ReadmeModel(MarkdownExtractionModel):            # HTML fields, Markdown input
    title = HtmlBaseField(query=css("h1::text"))
    sections = HtmlBaseField(query=css("h2::text"), multiple=True)

ReadmeModel().extract(markdown_text)
```

`parser.markdown_source` keeps the original text. Runnable: [`examples/03_markdown.py`](../examples/03_markdown.py).

## Composing formats

Real sites nest formats. Because every parser takes a plain string and every query returns plain values, you chain them. The general recipe: **extract the string with the outer parser, feed it to the inner one.**

### JSON inside HTML

```python
html = response.as_html_parser()
script = html.extract_value(css('script#__NEXT_DATA__::text'))      # <script type="application/json">
data = JsonParser(script)
data.extract_values(jmes_path("props.pageProps.items[].title"))
```

When the JSON is a JavaScript literal (`var data = [...];`), cut it out first:

```python
import re
literal = re.search(r"var data = (\[.*?\]);", script_text, re.S).group(1)
JsonParser(literal)
```

Runnable against a real site: [`examples/04_json_inside_html.py`](../examples/04_json_inside_html.py).

### Markdown inside JSON

```python
release = response.as_json_parser()
notes = MarkdownParser(release.extract_value(jmes_path("body")))
notes.extract_values(css("h2::text"))
```

Runnable: [`examples/05_markdown_inside_json.py`](../examples/05_markdown_inside_json.py).

### Markdown inside JSON inside a script tag

```python
script = response.as_html_parser().extract_value(css('script[data-target="react-app.embeddedData"]::text'))
lines = JsonParser(script).extract_value(jmes_path('payload."codeViewBlobLayoutRoute.StyledBlob".rawLines'))
readme = MarkdownParser("\n".join(lines))
readme.extract_values(css("h2::text"))
```

HTML → JSON → Markdown, three parsers, no special support needed. Runnable (GitHub file page): [`examples/06_markdown_in_json_in_script.py`](../examples/06_markdown_in_json_in_script.py).

> Sites change the shape of their embedded payloads without notice. Keep each hop in its own small function so a breakage is easy to localise.

Other combinations follow the same pattern: JSON that contains an HTML fragment (`HtmlParser(json_value)`) and a JSON string that is itself JSON-encoded (`JsonParser(json.loads(...))`).

## Images and OCR

With the `ocr` extra (and Tesseract installed), an image can be a data source. `image_text_extractor()` plugs into any `HtmlBaseField`:

```python
from xcrap.ocr import extract_image_text, image_text_extractor

class CaptchaPage(HtmlExtractionModel):
    code = HtmlBaseField(query=css("img.code"), extractor=image_text_extractor(lang="eng"))

extract_image_text("photo.png")           # path, bytes or PIL.Image -> str
```

The extractor reads the element's `src` (or `data-src`) and opens it as a **local file path**, so download remote images first (for example with a client) and pass the bytes to `extract_image_text()`.

## Which tool when?

| You have… | Use |
| --- | --- |
| One value, once | `parser.extract_value` |
| A list of simple values | `parser.extract_values` |
| A repeated block with several fields | `extract_models(Model, query)` |
| A whole page structure | `extract_model(PageModel)` with nested fields |
| Structure defined outside the code | [Factories](factories.md) |

# Utilities, factories and errors

```python
from xcrap.utils import MODERN_USER_AGENTS, Randomizer, Rotator, StaticPaginator   # also in xcrap.core
```

## Rotator

```python
proxies = Rotator(["http://p1:8080", "http://p2:8080", "http://p3:8080"])

proxies.current     # 'http://p1:8080' (does not advance)
proxies.rotate()    # advances and returns the new current (alias: proxies.next())
next(proxies)       # returns the current item, THEN advances; never raises StopIteration
proxies.reset()
len(proxies)

client = CurlCffiClient(proxy_url=lambda: next(proxies))   # a different proxy per request
```

## Randomizer

```python
Randomizer(["a", "b", "c"]).random()
Randomizer.user_agent()            # modern desktop UA
Randomizer.user_agent("firefox")   # chrome | firefox | safari | edge

client = HttpxClient(user_agent=lambda: Randomizer.user_agent("chrome"))
```

Both raise `EmptyListError` for an empty list.

## StaticPaginator

For pages addressed by a number in the URL. The template must contain `{page}`:

```python
paginator = StaticPaginator(initial_page=1, last_page=50, template_url="https://site.test/catalogue/page-{page}.html")

paginator.current        # page 1
paginator.next()         # page 2
paginator.previous()
paginator.set(10)
paginator.dump()         # current..last
paginator.dump(limit=5)  # at most 5 URLs
```

Outside `[min_page, last_page]` → `PageOutOfRangeError`; template without `{page}` → `InvalidUrlError`.

Read the range from the first page (and reuse its response):

```python
import re

tracked = await StaticPaginator.create_with_tracking(
    client=HttpxClient(),
    request="https://site.test/catalogue/page-1.html",          # URL or dict of fetch() arguments
    template_url="https://site.test/catalogue/page-{page}.html",
    trackers={
        "current_page": {"query": css("li.current")},
        "last_page": {"query": css("li.current"), "transformer": lambda raw: int(re.findall(r"\d+", raw)[-1])},
    },
)
paginator, first_response, first_parser = tracked["paginator"], tracked["response"], tracked["parser"]
```

A tracker has `query`, optional `extractor(selector)` and optional `transformer(raw) -> int` (default: the first number in the value). Feed `paginator.dump()` to `fetch_many()` or to a spider's `start_urls`.

## Factories

Build clients and models from plain configuration (JSON, YAML, a database). Everything is allow-listed:

```python
from xcrap.clients import CurlCffiClient, HttpxClient
from xcrap.extractor import HtmlExtractionModel, JsonExtractionModel, XmlExtractionModel
from xcrap.factory import create_client, create_extraction_model

client = create_client("httpx", {"httpx": HttpxClient, "curl": CurlCffiClient}, {"user_agent": "my-bot/1.0"})

model = create_extraction_model(
    {
        "type": "html",
        "model": {
            "title": {"query": {"type": "css", "value": "h1::text"}},
            "image": {"query": {"type": "css", "value": "img"}, "extractor": "attr:src"},
            "items": {
                "query": {"type": "css", "value": "li"},
                "multiple": True,
                "nested": {"type": "html", "model": {"name": {"query": {"type": "css", "value": "span::text"}}}},
            },
        },
    },
    allowed_models={"html": HtmlExtractionModel, "json": JsonExtractionModel, "xml": XmlExtractionModel},
    allowed_extractors={"attr": lambda name: lambda el: el.attrib.get(name)},   # pass {} if unused (required)
)

data = model.extract(html)
```

- Field keys: `query`, `multiple`, `limit`, `default`, `extractor` (string resolved through `allowed_extractors`, `"name:arg"`; HTML and XML only), `nested`.
- XML configs also accept `"namespaces"` and `"remove_namespaces"` next to `"type"`.
- Factory-built models are **instances**: call `model.extract(...)` (or `XmlParser.extract_model(model)`), not `HtmlParser.extract_model(model)`, which expects a class.

## Errors

All framework errors derive from `XcrapError` (`from xcrap.core import XcrapError`):

| Error | When |
| --- | --- |
| `DependencyMissingError` | Optional extra not installed (also an `ImportError`) |
| `EmptyListError` | `Rotator`/`Randomizer` with no values |
| `InvalidUrlError`, `PageOutOfRangeError` (`StaticPaginatorError`) | Paginator misuse |
| `PageParsingFailureError`, `InvalidPageValueError` (`TrackingError`) | Tracker found nothing / not an integer |
| `InvalidMarkdownBody` | Markdown body cannot be parsed |
| `DropItem` | Raised by you in a pipeline |

HTTP failures are not exceptions: check `response.is_success()`.

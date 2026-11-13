---
name: xcrap-python-best-practices
description: Conventions, project structure, testing strategy and common mistakes for scrapers and spiders built with Xcrap for Python (the `xcrap` PyPI package). Use when writing, reviewing, refactoring or debugging an Xcrap Python scraper or spider, when it returns empty or wrong data, gets blocked, breaks after a site change, or when setting up a new Python scraping project with Xcrap. Complements the `xcrap-python` skill, which documents the API.
---

# Xcrap for Python: best practices

The API lives in the `xcrap-python` skill. This one is about building scrapers that stay correct and maintainable.

## Rules

1. **Three layers, never mixed.** Client fetches; extraction model reads raw strings; a **pydantic model** cleans, converts and validates. No `float(...)`, `strip()` or `urljoin` scattered through extraction code or callbacks.
2. **Declarative over imperative.** Describe data with `HtmlExtractionModel` / `JsonExtractionModel` / `XmlExtractionModel` instead of chains of `selector.css()` in callbacks. Use `extractor=` only for element-level reads (attributes, sub-queries).
3. **Lightest client that works.** `HttpxClient` → `CurlCffiClient` → `PlaywrightClient` → `SeleniumBaseClient`. A browser is the last resort.
4. **Structured data first.** JSON endpoints, `__NEXT_DATA__`, JSON-LD and inline state beat markup: more stable, already typed.
5. **Validate every item.** Extraction returns `None` for missing elements instead of raising, so required fields are only enforced by your pydantic model. Declare optional fields as `X | None = None` on purpose.
6. **Fail loudly on required data.** Don't give required fields an extraction `default` or a lenient validator. A site change should raise a `ValidationError` that says which field broke, not silently produce empty rows.
7. **Check `response.is_success()`.** Clients return failures as responses. Selenium-based clients always report `200`, so check for an expected element too.
8. **Be polite and predictable.** Bounded `concurrency`, a `request_delay`, `max_retries` with `retry_delay`, realistic user agents, `max_requests` while developing. Respect the site's terms and `robots.txt` (spiders do not read it for you), and don't collect personal data you're not allowed to.

## Project layout

One package per target site:

```
scrapers/
└── example_store/
    ├── __init__.py
    ├── client.py        # configured client (UA, proxy, retries); subclass for browser actions
    ├── models.py        # extraction models (raw shape)
    ├── schemas.py       # pydantic models (clean shape) + reusable Annotated types
    ├── spider.py        # Spider / ModelSpider, or scraper.py for one-off fetch → extract → validate
    └── pipelines.py     # storage, de-duplication, enrichment
tests/
└── example_store/
    ├── fixtures/        # saved HTML/JSON/XML responses
    ├── test_models.py
    └── test_spider.py
```

- Models and schemas are pure and need no network, so they are trivial to test.
- Inject the client (`Spider(client=...)`, or a `client` parameter on scraper functions) so tests can swap it.
- Name raw fields after what the page shows (`price_text`) and clean fields after what your domain needs; rename with pydantic aliases or a `model_validator`.

## The validation layer

Reusable annotated types keep schemas short:

```python
import re
from typing import Annotated
from urllib.parse import urljoin

from pydantic import BaseModel, BeforeValidator, HttpUrl, ValidationInfo, field_validator


def clean_text(value):
    return " ".join(value.split()) if isinstance(value, str) else value


def parse_decimal_comma(value):  # "R$ 1.234,56" -> 1234.56
    if isinstance(value, str):
        return float(re.sub(r"[^\d,]", "", value).replace(",", "."))
    return value


Text = Annotated[str, BeforeValidator(clean_text)]
BrlPrice = Annotated[float, BeforeValidator(parse_decimal_comma)]


class Product(BaseModel):
    name: Text
    price: BrlPrice
    url: HttpUrl
    badge: Text | None = None

    @field_validator("url", mode="before")
    @classmethod
    def resolve_url(cls, value, info: ValidationInfo):
        base_url = (info.context or {}).get("base_url")
        return urljoin(base_url, value) if base_url and isinstance(value, str) else value


product = Product.model_validate(raw, context={"base_url": response.url})
```

- Know the site's number format: `"1.234"` is 1234 in pt-BR and 1.234 in en-US. Write one parser per format instead of guessing.
- Resolve relative URLs against the page they came from (`context={"base_url": response.url}`, or `response.urljoin()` in spiders).
- One broken card shouldn't discard a whole page: validate per item, log the `ValidationError`s and keep the rest.

```python
from pydantic import ValidationError

products, failures = [], []
for item in raw["products"]:
    try:
        products.append(Product.model_validate(item, context={"base_url": url}))
    except ValidationError as error:
        failures.append(error)
```

In spiders, yield the pydantic instance: `JsonLinesPipeline` dumps it with `model_dump()`.

## Selectors that survive redesigns

- Prefer stable hooks: `id`, `data-*`, `itemprop`, ARIA attributes, semantic tags (`h1`, `article`, `time[datetime]`), not generated classes (`.css-1x2y3z`).
- Scope with nested models: the card model uses `css("h2::text")`, not `css(".grid > div:nth-child(2) h2::text")`.
- Read machine-readable attributes: `time::attr(datetime)`, `meta[itemprop=price]::attr(content)`, `::attr(data-price)`.
- Prefer CSS. In nested models, XPath must be relative (`.//span/text()`). `//span` searches the whole document.
- Use `normalize-space()` / `string()` in XPath, or the `Text` type, to collapse whitespace.

## XML

- Use `XmlParser`/`XmlExtractionModel`, not `HtmlParser`, for feeds and sitemaps. HTML parsing lowercases names and "repairs" XML.
- Choose one namespace strategy per document: `remove_namespaces=True` (simplest), registered `namespaces`, or `local-name()`.
- Item paths are relative (`title/text()`), never `//title`.

## Spiders

- Use spiders for discovery (follow links, unknown page counts); use `fetch_many()` for known URL lists.
- Set `max_requests` and `max_depth` while developing, and keep `concurrency`/`request_delay` conservative in production.
- Put transport concerns (retries, proxies, user agents, browser actions) on the **client**, not in callbacks.
- Carry context with `meta` (category, list URL), not with spider instance attributes shared between requests.
- Handle `429`/`503` in `on_error`/`errback` (re-queue with `dont_filter=True`); count and log the rest.

## Testing

Unit tests never touch the network:

```python
from pathlib import Path

from pydantic import TypeAdapter

from scrapers.example_store.models import CatalogPageModel
from scrapers.example_store.schemas import Product
from xcrap.extractor import HtmlParser

FIXTURES = Path(__file__).parent / "fixtures"


def test_catalog_page() -> None:
    raw = HtmlParser.load_file(str(FIXTURES / "catalog.html")).extract_model(CatalogPageModel)
    products = TypeAdapter(list[Product]).validate_python(raw["products"], context={"base_url": "https://shop.test/c/1"})

    assert len(products) == 24
    assert products[0].price == 129.9
```

- Save fixtures from real responses (`response.text`), including edge cases (empty listing, missing optional field, last page).
- Test schemas separately with tricky strings (`"R$ 1.234,56"`, `"Esgotado"`, relative URLs).
- Test spiders with a fake client serving canned pages (see the `xcrap-python` skill, spiders reference).
- Keep an opt-in live smoke test to notice markup changes early.

## Debugging checklist

1. **Is the response what you think?** Log `response.status` and save `response.text`. Challenge pages, consent walls and login redirects often return 200.
2. **Is the data in the HTML at all?** If only the browser shows it, find the JSON endpoint or embedded state before switching to Playwright.
3. **Does the query match the fetched document?** Test against the saved file with `HtmlParser.load_file`, not against DevTools (which shows the DOM after JavaScript).
4. **Field is `None`?** The selector is wrong, the element is optional, or the content is rendered by JavaScript.
5. **Every item of a list has the same value?** An absolute XPath (`//...`) inside a nested model.
6. **`ValidationError`?** Read `error.errors()[i]["loc"]` and look at that raw value: locale, placeholder text (`"Consulte"`), unexpected format.
7. **Blocked (403/429, challenges)?** Lower concurrency, add `request_delay`, rotate user agents, then `CurlCffiClient`, proxies, and only then a browser client.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| `extractor=lambda text: text.strip()` | Extractors receive a parsel `Selector`: `lambda el: el.css("::text").get()`. Better: query `::text` and clean in pydantic. |
| `xpath("//span/text()")` in a nested model | `xpath(".//span/text()")` or `css("span::text")`. |
| Forgetting `::text` / `::attr()` | Without them you get the element's HTML. |
| `retry_delay=2` meaning seconds | Delays are milliseconds: `retry_delay=2000`. |
| `HttpxClient(proxy="http://proxy:8080")` | `HttpxClient` ignores `proxy` and treats `proxy_url` as a URL prefix. Use `CurlCffiClient(proxy_url=...)` for a proxy server. |
| `parser.extract_model(factory_built_model)` on `HtmlParser` | Factory models are instances: `model.extract(parser.selector)`. |
| `create_extraction_model(config, allowed_models)` | `allowed_extractors` is required; pass `{}`. |
| Passing `actions` through a spider | Spiders don't forward them. Subclass the client and set default actions. |
| Trusting `status == 200` from Selenium clients | They always report 200. Check the content. |
| Not checking `is_success()` | Failed requests are responses (`500` with the error text, or the real status for `HttpxClient`). |
| `HtmlParser` for RSS/sitemaps | `XmlParser` / `response.as_xml_parser()`. |
| Calling `asyncio.run(spider.crawl())` inside running async code | `await spider.crawl()`; `spider.run()` only in scripts. |

---
name: xcrap-python
description: How to build web scrapers and crawlers in Python with Xcrap for Python (the `xcrap` package on PyPI, asyncio-based). Use whenever Python code imports `xcrap` (`xcrap.clients`, `xcrap.extractor`, `xcrap.spiders`, `xcrap.utils`, `xcrap.factory`), or when the user asks to scrape, crawl or extract data in Python with Xcrap — choosing a client (httpx, curl-cffi, Playwright, Selenium, SeleniumBase), writing extraction models for HTML, JSON, Markdown or XML (RSS, Atom, sitemaps), writing spiders and pipelines, paginating, rotating proxies, or building scrapers from configuration.
---

# Xcrap for Python

Xcrap is an `asyncio` web scraping framework: interchangeable clients, declarative extraction models and Scrapy-inspired spiders. It is the Python port of the Node.js Xcrap, with the same concepts and names in snake_case.

```
URL ──▶ Client.fetch() ──HttpResponse──▶ Parser / ExtractionModel ──dicts/lists──▶ pydantic model ──▶ your code
        xcrap.clients                    xcrap.extractor                              validation          (or Spider pipelines)
```

1. **Client** fetches a URL and returns an `HttpResponse` (never raises on HTTP/network failures).
2. **Extraction** turns the body into plain `dict`s and `list`s with *models* (declarative) or *parsers* (ad-hoc queries).
3. **Validation**: Xcrap for Python has no transformer package. Clean and type the raw values with **pydantic** (already a dependency).
4. **Spider** (optional) drives the loop for whole sites: scheduling, de-duplication, concurrency, pipelines and stats.

## Installation

```bash
pip install xcrap                 # httpx, parsel, jmespath, pydantic, markdown, cryptography
pip install "xcrap[curl]"         # CurlCffiClient (TLS impersonation)
pip install "xcrap[playwright]"   # PlaywrightClient, then: playwright install chromium
pip install "xcrap[selenium]"     # SeleniumClient
pip install "xcrap[seleniumbase]" # SeleniumBaseClient (undetected mode)
pip install "xcrap[ocr]"          # xcrap.ocr (needs the Tesseract binary)
```

Python 3.12+. Using a feature without its extra raises `DependencyMissingError` naming the extra to install. Everything public is re-exported from the sub-packages (`from xcrap.extractor import css`).

## End-to-end example

```python
import asyncio
from typing import Annotated
from urllib.parse import urljoin

from pydantic import BaseModel, BeforeValidator, HttpUrl, TypeAdapter, ValidationInfo, field_validator

from xcrap.clients import HttpxClient
from xcrap.extractor import HtmlBaseField, HtmlExtractionModel, HtmlNestedField, css


# 1. Extraction: where the raw strings are
class ProductModel(HtmlExtractionModel):
    name = HtmlBaseField(query=css(".product__title::text"))
    price = HtmlBaseField(query=css(".product__price::text"))
    url = HtmlBaseField(query=css("a.product__link::attr(href)"))
    badge = HtmlBaseField(query=css(".product__badge::text"))  # None when missing


class CatalogPageModel(HtmlExtractionModel):
    products = HtmlNestedField(query=css(".grid .product"), model=ProductModel, multiple=True)


# 2. Validation: what the clean data looks like
Text = Annotated[str, BeforeValidator(lambda v: " ".join(v.split()) if isinstance(v, str) else v)]


class Product(BaseModel):
    name: Text
    price: float
    url: HttpUrl
    badge: Text | None = None

    @field_validator("price", mode="before")
    @classmethod
    def parse_price(cls, value):
        return value.replace("$", "").replace(",", "") if isinstance(value, str) else value

    @field_validator("url", mode="before")
    @classmethod
    def resolve_url(cls, value, info: ValidationInfo):
        base_url = (info.context or {}).get("base_url")
        return urljoin(base_url, value) if base_url and isinstance(value, str) else value


# 3. Execution
async def scrape_catalog(page_url: str) -> list[Product]:
    client = HttpxClient()
    response = await client.fetch(url=page_url, max_retries=2, retry_delay=1000)

    if not response.is_success():
        raise RuntimeError(f"GET {page_url} -> {response.status}")

    raw = response.as_html_parser().extract_model(CatalogPageModel)

    return TypeAdapter(list[Product]).validate_python(raw["products"], context={"base_url": page_url})


print(asyncio.run(scrape_catalog("https://example.com/catalog")))
```

## References

Read the one that matches the task:

- [references/clients.md](references/clients.md): choosing a client, `fetch`/`fetch_many`, retries, failures, proxies and user agents, browser `actions`, decryption, custom clients.
- [references/extraction.md](references/extraction.md): queries, `HtmlParser`/`HtmlExtractionModel`, JSON, Markdown, composing formats, OCR.
- [references/xml.md](references/xml.md): RSS, Atom and sitemaps with `XmlParser`/`XmlExtractionModel`, and XML namespaces.
- [references/spiders.md](references/spiders.md): `Spider`, `ModelSpider`, `Request`, callbacks, pipelines, settings, errors, offline tests.
- [references/utilities.md](references/utilities.md): `Rotator`, `Randomizer`, `StaticPaginator`, factories, the error hierarchy.

For conventions, project layout, testing and common mistakes, use the `xcrap-python-best-practices` skill.

## Key facts to keep in mind

- Everything network-related is `async`; run with `asyncio.run(main())`, or `spider.run()` for a blocking crawl.
- Durations (`retry_delay`, `request_delay`) are **milliseconds**.
- Queries are dicts built with `css()`, `xpath()` and `jmes_path()`; CSS supports parsel's `::text` and `::attr(name)`.
- A field's `extractor=` receives a parsel `Selector`, not a string.
- In nested models, an XPath starting with `//` searches the **whole document**. Use `.//` or a relative path.
- Clients return failures as responses: always check `response.is_success()`.

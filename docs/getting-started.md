# Getting started

## Requirements and installation

Xcrap needs **Python 3.12+**.

```bash
pip install xcrap
```

The core install is light (`httpx`, `parsel`, `jmespath`, `pydantic`, `markdown`, `cryptography`). Heavier capabilities are optional extras:

| Extra | Installs | Enables |
| --- | --- | --- |
| `xcrap[curl]` | `curl-cffi` | `CurlCffiClient` — browser TLS/HTTP2 impersonation for anti-bot protected sites |
| `xcrap[playwright]` | `playwright` | `PlaywrightClient` — JavaScript rendering. Then run `playwright install chromium` |
| `xcrap[selenium]` | `selenium` | `SeleniumClient` — WebDriver automation |
| `xcrap[ocr]` | `pytesseract`, `pillow` | `xcrap.ocr` — text from images. Needs the [Tesseract](https://github.com/tesseract-ocr/tesseract) binary installed |
| `xcrap[all]` | all of the above | |

Using a feature without its extra raises `DependencyMissingError`, which tells you the exact `pip install` to run.

## Your first scraper

```python
import asyncio

from xcrap.clients import HttpxClient
from xcrap.extractor import HtmlBaseField, HtmlExtractionModel, HtmlNestedField, css


class AuthorModel(HtmlExtractionModel):
    name = HtmlBaseField(query=css("small.author::text"))
    link = HtmlBaseField(query=css("a::attr(href)"))


class QuoteModel(HtmlExtractionModel):
    text = HtmlBaseField(query=css("span.text::text"))
    author = HtmlNestedField(model=AuthorModel)  # no query: receives the current element
    tags = HtmlBaseField(query=css("div.tags a.tag::text"), multiple=True)


class QuotesPageModel(HtmlExtractionModel):
    quotes = HtmlNestedField(query=css("div.quote"), model=QuoteModel, multiple=True)


async def main() -> None:
    client = HttpxClient()
    response = await client.fetch(url="https://quotes.toscrape.com")

    data = response.as_html_parser().extract_model(QuotesPageModel)

    for quote in data["quotes"][:3]:
        print(quote["text"], "-", quote["author"]["name"], quote["tags"])


asyncio.run(main())
```

What happened, step by step:

1. A **client** fetched the URL and returned an [`HttpResponse`](clients.md#httpresponse).
2. `as_html_parser()` wrapped the body in an `HtmlParser`.
3. `extract_model()` walked the document following the **model**, returning plain `dict`s and `list`s.

The same script lives in [`examples/01_html_extraction.py`](../examples/01_html_extraction.py) (with books.toscrape.com).

## Going from one page to a whole site

When you need to follow links, paginate, de-duplicate and throttle, stop writing loops and use a [spider](spiders.md):

```python
from xcrap.extractor import css
from xcrap.spiders import Spider


class QuotesSpider(Spider):
    start_urls = ["https://quotes.toscrape.com"]

    async def parse(self, response):
        parser = response.as_html_parser()

        for quote in parser.extract_models(QuoteModel, css("div.quote")):
            yield quote                      # a dict -> an item

        for href in parser.extract_values(css("li.next a::attr(href)")):
            yield response.follow(href)      # a Request -> keep crawling
```

(`QuoteModel` is the model from the previous example.) Run it with `QuotesSpider().run()` (blocking, returns the stats) or `await QuotesSpider().collect()` (returns the items).

## Project layout

```
xcrap/
├── clients/     HttpxClient, CurlCffiClient, PlaywrightClient, SeleniumClient
├── core/        HttpClientBase, HttpResponse, errors, decryptor
├── extractor/   HtmlParser, JsonParser, MarkdownParser, extraction models, css/xpath/jmes_path
├── spiders/     Spider, ModelSpider, Request, SpiderResponse, pipelines, scheduler, stats
├── factory/     create_client, create_extractor, create_extraction_model
├── utils/       Rotator, Randomizer, StaticPaginator, decryption helpers
└── ocr/         extract_image_text, image_text_extractor
```

Everything public is re-exported from the sub-package (`from xcrap.extractor import css`), so you rarely need to import from a module path.

## Next steps

- Choose how to fetch: [Clients](clients.md)
- Learn every extraction feature: [Extraction](extraction.md)
- Crawl: [Spiders](spiders.md)
- Run something real: [Examples](../examples/README.md)

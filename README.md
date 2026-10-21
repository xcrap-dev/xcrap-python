# Xcrap for Python

**Xcrap is a modern web scraping framework.** It gives you interchangeable HTTP and browser clients, declarative extraction for HTML, JSON and Markdown, and Scrapy-inspired spiders for crawling whole sites — with one consistent, `asyncio`-native API.

This is the Python port of the Node.js [Xcrap](https://github.com/Xcrap-Cloud) framework, keeping the same concepts and vocabulary so scrapers translate between the two.

- **Declarative extraction** — describe the shape of your data with models, not loops of selectors.
- **Interchangeable clients** — `httpx`, `curl-cffi` (anti-bot TLS impersonation), Playwright, Selenium and SeleniumBase (undetected mode) behind one interface.
- **Every format, and formats inside formats** — HTML (CSS/XPath), JSON (JMESPath), Markdown; e.g. Markdown inside JSON inside a `<script>` tag.
- **Spiders** — scheduler, de-duplication, concurrency, throttling, retries, pipelines and stats.
- **Configuration-driven** — build clients and models from JSON with factories.
- **Batteries included** — user-agent/proxy rotation, static pagination, AES response decryption, OCR.

📚 **Full documentation: [docs/](docs/README.md)** · 🧪 **Runnable examples: [examples/](examples/README.md)**

## Installation

Requires Python 3.12+.

```bash
pip install xcrap
```

Optional extras:

```bash
pip install "xcrap[curl]"        # CurlCffiClient: TLS fingerprint impersonation (Cloudflare & co.)
pip install "xcrap[playwright]"  # PlaywrightClient: JavaScript rendering (then: playwright install chromium)
pip install "xcrap[selenium]"    # SeleniumClient: WebDriver automation
pip install "xcrap[seleniumbase]" # SeleniumBaseClient: undetected (UC) mode for bot-protected sites
pip install "xcrap[ocr]"         # Text from images (requires the Tesseract binary)
pip install "xcrap[all]"         # everything
```

## Quick start

```python
import asyncio

from xcrap.clients import HttpxClient
from xcrap.extractor import HtmlBaseField, HtmlExtractionModel, HtmlNestedField, css


# 1. Describe your data declaratively
class AuthorModel(HtmlExtractionModel):
    name = HtmlBaseField(query=css("small.author::text"))
    link = HtmlBaseField(query=css("a::attr(href)"))


class QuoteModel(HtmlExtractionModel):
    text = HtmlBaseField(query=css("span.text::text"))
    author = HtmlNestedField(model=AuthorModel)           # nested models are effortless
    tags = HtmlBaseField(query=css("div.tags a.tag::text"), multiple=True)


class QuotesPageModel(HtmlExtractionModel):
    quotes = HtmlNestedField(query=css("div.quote"), model=QuoteModel, multiple=True)


async def main():
    client = HttpxClient()

    # 2. Fetch the page
    response = await client.fetch(url="https://quotes.toscrape.com")

    # 3. Turn it into a parser and extract
    data = response.as_html_parser().extract_model(QuotesPageModel)

    for quote in data["quotes"][:3]:
        print(f"{quote['text']} — {quote['author']['name']} {quote['tags']}")


asyncio.run(main())
```

## Crawling with spiders

When you need to follow links, paginate and write results somewhere, let a spider drive:

```python
from xcrap.extractor import css
from xcrap.spiders import DropItem, ItemPipeline, JsonLinesPipeline, Spider


class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com"]
    concurrency = 4
    request_delay = 200      # ms between requests
    max_retries = 2

    async def parse(self, response):
        parser = response.as_html_parser()

        for quote in parser.extract_models(QuoteModel, css("div.quote")):
            yield quote                                   # a dict -> an item

        for href in parser.extract_values(css("li.next a::attr(href)")):
            yield response.follow(href)                   # a Request -> keep crawling


class RequireText(ItemPipeline):
    async def process_item(self, item, spider):
        if not item["text"]:
            raise DropItem("no text")
        return item


stats = QuotesSpider(pipelines=[RequireText(), JsonLinesPipeline("quotes.jsonl")]).run()
print(stats.items_scraped, "items in", round(stats.elapsed, 1), "s")
```

No `parse` needed for the common case — a `ModelSpider` is configured with `model`, `items_query` and `follow_query`. See the [spiders guide](docs/spiders.md), including [how it differs from Scrapy](docs/spiders.md#differences-from-scrapy).

## Choosing a client

```python
from xcrap.clients import CurlCffiClient, HttpxClient, PlaywrightClient, SeleniumBaseClient, SeleniumClient

HttpxClient()                                   # fast default for APIs and static HTML
CurlCffiClient(impersonate="chrome120")         # looks like a real browser to anti-bot systems
PlaywrightClient(headless=True)                 # runs JavaScript; supports actions
SeleniumClient(browser_type="chrome")           # WebDriver
SeleniumBaseClient(uc=True)                     # undetected Chrome: Cloudflare, CAPTCHAs
```

All of them accept `max_retries`, `retry_delay` and `headers` per fetch, and `user_agent` / `proxy_url` as a string **or a callable** for rotation. Browser clients take `actions` to click, scroll or wait before the HTML is captured:

```python
response = await PlaywrightClient().fetch(
    url="https://quotes.toscrape.com/js-delayed/",
    actions=[lambda page: page.wait_for_selector("div.quote")],
)
```

More in the [clients guide](docs/clients.md).

## More features

**JSON with JMESPath**

```python
from xcrap.extractor import JsonBaseField, JsonExtractionModel, JsonParser, jmes_path


class ProjectModel(JsonExtractionModel):
    name = JsonBaseField(query=jmes_path("title"))
    tags = JsonBaseField(query=jmes_path("tags"), multiple=True)


JsonParser('{"title": "Xcrap", "tags": ["python", "scraping"]}').extract_model(ProjectModel)
# {'name': 'Xcrap', 'tags': ['python', 'scraping']}
```

**Formats inside formats** — HTML → JSON → Markdown in four lines:

```python
script = response.as_html_parser().extract_value(css('script[data-target="react-app.embeddedData"]::text'))
lines = JsonParser(script).extract_value(jmes_path('payload."codeViewBlobLayoutRoute.StyledBlob".rawLines'))
readme = MarkdownParser("\n".join(lines))
```

**Custom extractors** receive the matched parsel `Selector`:

```python
price = HtmlBaseField(query=css(".price"), extractor=lambda el: float(el.css("::text").get().replace("$", "")))
```

**Automatic decryption** of AES-encrypted responses:

```python
from xcrap.core import decrypt_client
from xcrap.utils.decryption import DecryptConfig, DecryptKeyConfig

config = DecryptConfig(algorithm="aes-256-cbc", key=DecryptKeyConfig(value="..."), iv=DecryptKeyConfig(value="..."))

@decrypt_client(config)
class SecureClient(HttpxClient): ...
```

**Factories** build clients, extractors and models from configuration data:

```python
from xcrap.factory import create_client, create_extraction_model

client = create_client("httpx", allowed_clients={"httpx": HttpxClient}, options={"user_agent": "my-bot/1.0"})
model = create_extraction_model(
    {"type": "html", "model": {"title": {"query": {"type": "css", "value": "h1::text"}}}},
    allowed_models={"html": HtmlExtractionModel},
    allowed_extractors={},
)
```

**Rotation and pagination**: `Rotator`, `Randomizer`, `StaticPaginator` — see [utilities](docs/utilities.md).

## Documentation

| | |
| --- | --- |
| [Getting started](docs/getting-started.md) | Installation, first scraper, how the pieces fit |
| [Clients](docs/clients.md) | All clients, retries, concurrency, proxies, actions, decryption, custom clients |
| [Extraction](docs/extraction.md) | HTML, JSON, Markdown, composing formats, OCR |
| [Spiders](docs/spiders.md) | Crawling, pipelines, settings, statistics, Scrapy comparison |
| [Utilities](docs/utilities.md) | Rotator, Randomizer, StaticPaginator, errors |
| [Factories](docs/factories.md) | Configuration-driven scrapers |
| [Examples](examples/README.md) | 18 runnable scripts against real sites |

## Development

```bash
poetry install
poetry run pytest                                       # tests
poetry run pytest --cov=xcrap --cov-report=term-missing # with coverage
poetry run ruff check .
```

The example scripts hit real websites ([quotes.toscrape.com](https://quotes.toscrape.com), [books.toscrape.com](https://books.toscrape.com), the GitHub API…) and are not part of the test suite.

---
Made with ❤️ by Marcuth <contact@marcuth.dev>

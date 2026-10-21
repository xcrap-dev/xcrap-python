# Examples

Runnable scripts against real, public websites made for scraping practice or with open APIs. Run any of them from the repository root:

```bash
poetry run python examples/01_html_extraction.py
```

> On Windows terminals set `PYTHONIOENCODING=utf-8` to see typographic quotes correctly.

Sites change. If one stops working, the *technique* shown is still valid — adapt the selectors.

## Extraction (no spiders)

| Script | Site | Shows |
| --- | --- | --- |
| [`01_html_extraction.py`](01_html_extraction.py) | books.toscrape.com | HTML models, nested models, custom `extractor`, CSS + XPath, defaults |
| [`02_json_api.py`](02_json_api.py) | quotes.toscrape.com API | JSON models with JMESPath, nested JSON, ad-hoc queries |
| [`03_markdown.py`](03_markdown.py) | raw GitHub README | `MarkdownParser`, `MarkdownExtractionModel` |
| [`04_json_inside_html.py`](04_json_inside_html.py) | quotes.toscrape.com/js | JSON living in a `<script>` tag |
| [`05_markdown_inside_json.py`](05_markdown_inside_json.py) | GitHub API | Markdown inside a JSON field |
| [`06_markdown_in_json_in_script.py`](06_markdown_in_json_in_script.py) | github.com | HTML → `<script>` JSON → Markdown |

## Clients and utilities

| Script | Site | Shows | Needs |
| --- | --- | --- | --- |
| [`10_fetch_many_and_pagination.py`](10_fetch_many_and_pagination.py) | books.toscrape.com | `StaticPaginator` with tracking, `fetch_many` with concurrency/delay/retries | |
| [`11_client_curl_cffi.py`](11_client_curl_cffi.py) | tls.peet.ws | TLS fingerprints of `HttpxClient` vs `CurlCffiClient` | `xcrap[curl]` |
| [`12_client_playwright.py`](12_client_playwright.py) | quotes.toscrape.com/js-delayed | JavaScript rendering and `actions` | `xcrap[playwright]` + `playwright install chromium` |
| [`13_rotation_and_factories.py`](13_rotation_and_factories.py) | httpbin.org, quotes.toscrape.com | `Rotator`, `Randomizer`, `create_client`, `create_extraction_model` | |
| [`14_decryption.py`](14_decryption.py) | offline | AES response decryption | |
| [`15_client_seleniumbase.py`](15_client_seleniumbase.py) | quotes.toscrape.com/js, bot.sannysoft.com | Undetected browsing and SeleniumBase actions | `xcrap[seleniumbase]` + Chrome |

## Spiders

| Script | Site | Shows | Needs |
| --- | --- | --- | --- |
| [`20_spider_callbacks.py`](20_spider_callbacks.py) | quotes.toscrape.com | Callbacks, `follow`, settings, stats | |
| [`21_spider_pipelines.py`](21_spider_pipelines.py) | quotes.toscrape.com | Pipelines, `DropItem`, pydantic items, JSON Lines | |
| [`22_spider_declarative.py`](22_spider_declarative.py) | quotes.toscrape.com | `ModelSpider`, `stream()` | |
| [`23_spider_json_api.py`](23_spider_json_api.py) | quotes.toscrape.com API | Crawling a JSON API | |
| [`24_spider_list_detail.py`](24_spider_list_detail.py) | books.toscrape.com | List → detail, `meta`, `priority`, `errback` | |
| [`25_spider_playwright.py`](25_spider_playwright.py) | quotes.toscrape.com/js | A spider on a browser client | `xcrap[playwright]` |

Be polite: these scripts use small limits, `request_delay` and `max_requests`. Keep them when you adapt the code to other sites.

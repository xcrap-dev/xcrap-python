# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Xcrap for Python is an `asyncio` web scraping **framework** (clients + declarative extraction + Scrapy-inspired spiders). It is the Python port of the Node.js Xcrap monorepo that lives next to it in `../../packages/`; keep concepts and names aligned with that version. Python 3.12+, managed with Poetry.

## Commands

```bash
poetry install --all-extras            # dev setup incl. curl-cffi, playwright, selenium, seleniumbase, ocr
poetry run pytest                      # whole suite
poetry run pytest tests/spiders/test_spider.py::test_model_spider   # a single test
poetry run pytest --cov                # coverage; FAILS below 100% (fail_under in pyproject.toml)
poetry run ruff check . && poetry run ruff format --check .         # what CI runs (drop --check to fix)
poetry build                           # wheel + sdist in dist/
poetry lock                            # required after editing dependencies/extras in pyproject.toml
```

- On this Windows machine the default `python` is 3.9; Poetry prints "currently activated Python version 3.9.13 is not supported" and then correctly falls back to 3.12. Always go through `poetry run`.
- Tests never touch the network. `examples/*.py` do (quotes.toscrape.com, books.toscrape.com, GitHub, …) and are run manually: `poetry run python examples/20_spider_callbacks.py` (set `PYTHONIOENCODING=utf-8` on Windows).
- Ruff: line length 134, `E501` ignored under `tests/`. `.pre-commit-config.yaml` runs ruff on commit; CI (`.github/workflows/ci.yml`) runs lint, format check, tests with coverage, and a wheel smoke test.
- The version lives in **two places** that must be bumped together: `pyproject.toml` and `xcrap/__init__.py` (`__version__`).
- Docs (`README.md`, `docs/`, `examples/`) are written in English.

## Architecture

The data flow is `Client.fetch(url) → HttpResponse → Parser/ExtractionModel → dicts/lists`, and a `Spider` drives that loop for whole sites.

- **Clients** (`xcrap/clients/`, base in `core/http_client_base.py`): `HttpxClient`, `CurlCffiClient`, `PlaywrightClient`, `SeleniumClient`, `SeleniumBaseClient` implement `fetch()` / `fetch_many()` and all return `core.HttpResponse`. Everything else (parsers, spiders, factories) depends only on that interface, so clients are interchangeable.
- **Extraction** (`xcrap/extractor/`): queries are plain dicts from `css()` / `xpath()` / `jmes_path()`. `HtmlExtractionModel`, `JsonExtractionModel` and `MarkdownExtractionModel` collect their `*Field` class attributes in `__init_subclass__` (inheritance merges parent fields) or take a `shape` dict at construction (what the factories use). Markdown is rendered to HTML and queried as HTML (`MarkdownParser` subclasses `HtmlParser`). Formats compose by passing extracted strings to another parser; there is no special nesting API.
- **Spiders** (`xcrap/spiders/`): `Spider.crawl()` seeds a `Scheduler` (priority queue + URL de-duplication), starts `concurrency` worker tasks that call `client.fetch` once per request (not `fetch_many`), run the callback, and route what it yields: `Request` → scheduler, anything else → item pipelines. `ModelSpider` is the declarative variant built on `HtmlParser.extract_models`. Retries, proxies and user agents belong to the client, not the spider (no download middlewares by design).
- **Factories** (`xcrap/factory/`): build clients, extractors and models from plain config; they are allow-list based (`allowed_clients`, `allowed_models`, `allowed_extractors`).
- `xcrap/core/__init__.py` re-exports utilities (`Rotator`, `Randomizer`, `StaticPaginator`) and errors; `xcrap/utils/` holds their implementation.

## Behaviors that are easy to get wrong

- **Clients do not raise on HTTP/network failures.** They return an `HttpResponse` (status `500` with the error text for exceptions). Only `HttpxClient` retries on non-2xx statuses; the browser and curl clients retry exceptions only. Selenium-based clients cannot read status codes and always report `200`.
- `HttpxClient` uses `proxy_url` as a **URL prefix** and ignores `proxy`; the other clients use it as a real proxy server. `user_agent`, `proxy_url` and `proxy` may be callables (resolved per request through `utils.resolve`), which is how rotation works.
- A field's `extractor=` receives a parsel `Selector`, not a string. Factory-built models are **instances**; `parser.extract_model()` expects a model **class**.
- `create_extraction_model` requires `allowed_extractors` (pass `{}` if unused). Browser `actions` are not forwarded by spiders; subclass the client to set defaults (see `examples/25_spider_playwright.py`).
- Delays (`retry_delay`, `request_delay`) are in milliseconds.

## Optional dependencies and the 100% coverage rule

Every optional integration follows one pattern: `try: import x / except ImportError: x = None`, then the constructor and `fetch()` raise `DependencyMissingError` (message tells the user which `xcrap[extra]` to install). Because the `except` branch only runs when the package is absent, `tests/test_import_fallbacks.py::load_without()` executes a throwaway copy of the module with the package blocked in `sys.modules`. New optional integrations need such a test, plus mocks for the heavy library in their client tests (no real browsers in the suite), or coverage drops below 100% on machines where the extra is installed.

When adding a dependency or extra, update `pyproject.toml` (extras table and `all`), run `poetry lock`, and document it in `README.md` and `docs/getting-started.md`.

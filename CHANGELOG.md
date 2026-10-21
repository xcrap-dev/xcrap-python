# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows [Semantic Versioning](https://semver.org/) (while below 1.0, minor versions may include breaking changes).

## [0.1.0] - 2026-10-20

First public release of Xcrap for Python, a scraping framework with parity to the Node.js version.

### Highlights

- **Spiders**: Scrapy-inspired `Spider` and declarative `ModelSpider`, with requests, callbacks, scheduler, de-duplication, concurrency and throttling, item pipelines (`DropItem`, JSON Lines export) and statistics.
- **Five interchangeable clients**: `HttpxClient`, `CurlCffiClient` (TLS impersonation), `PlaywrightClient`, `SeleniumClient` and `SeleniumBaseClient` (undetected mode), all with retries, `fetch_many` and `actions` for browsers.
- **Markdown extraction** next to HTML and JSON, so formats can be chained (for example HTML → JSON in a script tag → Markdown).
- **Utilities**: `Rotator`, `Randomizer`, `StaticPaginator` with automatic page tracking, OCR text extraction.
- **Documentation and examples**: a full guide in `docs/` and 18 runnable scripts in `examples/`.

### Added

- `xcrap.spiders` (`Spider`, `ModelSpider`, `Request`, `SpiderResponse`, `ItemPipeline`, `MemoryPipeline`, `JsonLinesPipeline`, `SpiderStats`).
- `CurlCffiClient`, `PlaywrightClient`, `SeleniumClient`, `SeleniumBaseClient`.
- `MarkdownParser`, `MarkdownExtractionModel`, `HttpResponse.as_json_parser()` / `as_markdown_parser()`.
- `Rotator`, `Randomizer`, `StaticPaginator`, `xcrap.ocr`, and a `XcrapError` hierarchy (`DependencyMissingError`, `DropItem`, …).
- Optional extras: `curl`, `playwright`, `selenium`, `seleniumbase`, `ocr`, `all`.

### Changed

- `HttpxClient` now follows redirects.
- `HtmlParser` exposes `root` as an alias of `selector`.

### Notes

- `HttpxClient` still treats `proxy_url` as a URL prefix and ignores `proxy`.
- Browser clients cannot read HTTP status codes or headers through WebDriver; `SeleniumClient` and `SeleniumBaseClient` report `200` for any rendered page.
- Requires Python 3.12 or newer.

[0.1.0]: https://github.com/xcrap-dev/xcrap-python/releases/tag/v0.1.0

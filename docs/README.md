# Xcrap for Python — Documentation

Xcrap is a **web scraping framework**: it gives you the pieces to fetch pages, extract structured data and crawl entire sites, and a consistent way to put them together. This is the Python port of the Node.js [Xcrap](https://github.com/Xcrap-Cloud) framework, with the same ideas and the same vocabulary.

## Reading order

| Guide | You will learn |
| --- | --- |
| [Getting started](getting-started.md) | Installation, optional extras, your first scraper, and the mental model behind the framework |
| [Clients](clients.md) | Fetching pages: `HttpxClient`, `CurlCffiClient`, `PlaywrightClient`, `SeleniumClient`, `SeleniumBaseClient`, retries, concurrency, proxies, user agents, decryption, writing your own client |
| [Extraction](extraction.md) | Turning documents into data: HTML, JSON, Markdown, nesting formats inside each other, custom extractors, OCR |
| [Spiders](spiders.md) | Crawling: `Spider`, `ModelSpider`, requests, callbacks, pipelines, settings, stats — and how it differs from Scrapy |
| [Utilities](utilities.md) | `Rotator`, `Randomizer`, `StaticPaginator`, the error hierarchy |
| [Factories](factories.md) | Building clients, extractors and models from plain configuration (JSON, YAML, a database…) |
| [Examples](../examples/README.md) | Runnable scripts against real sites, one per technique |

## The framework in one picture

```
            ┌──────────┐   HttpResponse   ┌──────────────┐   dicts / lists   ┌────────────┐
 URL ─────► │  Client  │ ───────────────► │ Parser/Model │ ────────────────► │ your code  │
            └──────────┘                  └──────────────┘                   └────────────┘
    httpx · curl-cffi · playwright         HTML · JSON · Markdown            (or pipelines
    selenium · seleniumbase                css · xpath · jmespath             when using a Spider)

 A Spider drives this loop for you: it schedules requests, runs callbacks, follows links,
 de-duplicates URLs, throttles, counts everything and feeds items to pipelines.
```

Three ideas run through everything:

1. **Clients are interchangeable.** Every client implements `fetch()` / `fetch_many()` and returns the same `HttpResponse`. Swapping `HttpxClient` for `PlaywrightClient` never touches your extraction code.
2. **Extraction is declarative.** You describe the *shape* of the data with models and queries; Xcrap walks the document. Models nest, inherit and can be built from configuration.
3. **Formats compose.** An HTML page can contain a JSON script that contains a Markdown string. Each layer is just another parser (see [Extraction → Composing formats](extraction.md#composing-formats)).

## Conventions

- Everything network-related is `async` (`asyncio`). Use `asyncio.run(main())`, or `Spider.run()` for a blocking crawl.
- Durations such as `retry_delay` and `request_delay` are **milliseconds**.
- Queries are small dicts built with `css()`, `xpath()` and `jmes_path()`.
- Clients **do not raise** on HTTP failures: they return an `HttpResponse` whose `status` tells you what happened. Check `response.is_success()`.

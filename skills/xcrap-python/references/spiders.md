# Spiders

```python
from xcrap.spiders import (
    DropItem, ItemPipeline, JsonLinesPipeline, MemoryPipeline, ModelSpider, Request, Spider,
)
```

A spider starts from URLs, turns each response into **items** and **more requests**, and handles scheduling, URL de-duplication, concurrency, throttling, errors and statistics. Use one whenever you follow links or paginate an unknown number of pages; for a known URL list, `client.fetch_many()` is enough.

```python
class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com"]
    concurrency = 4
    request_delay = 250

    async def parse(self, response):
        parser = response.as_html_parser()

        for quote in parser.extract_models(QuoteModel, css("div.quote")):
            yield quote                                   # item

        for href in parser.extract_values(css("li.next a::attr(href)")):
            yield response.follow(href)                   # request (same callback by default)
```

## Running

| Call | Returns |
| --- | --- |
| `spider.run()` | `SpiderStats` (blocking, for scripts) |
| `await spider.crawl()` | `SpiderStats`; items go to pipelines |
| `await spider.collect()` | `list` of items |
| `async for item in spider.stream()` | items while crawling; breaking out cancels the crawl |

Constructor: `Spider(client=None, pipelines=None, **settings)`; without a client an `HttpxClient` is created.

## Callbacks

A callback receives a `SpiderResponse` and may be a function, coroutine, generator or async generator. Yielded/returned values are classified: `Request` → scheduled, `None` → ignored, iterables → each element, anything else (`dict`, pydantic model, …) → item.

`SpiderResponse` is an `HttpResponse` plus `request`, `url`, `meta`, `urljoin(url)`, `follow(url, callback=None, **request_kwargs)` and `follow_all(urls, ...)`.

```python
class BooksSpider(Spider):
    start_urls = ["https://books.toscrape.com"]

    async def parse(self, response):
        parser = response.as_html_parser()

        for href in parser.extract_values(css("article.product_pod h3 a::attr(href)")):
            yield response.follow(href, callback="parse_book", meta={"list_url": response.url}, priority=10)

        for href in parser.extract_values(css("li.next a::attr(href)")):
            yield response.follow(href)

    async def parse_book(self, response):
        raw = response.as_html_parser().extract_model(BookModel)
        yield Book.model_validate(raw, context={"base_url": response.url})   # pydantic item
```

Override `start_requests()` (sync or async generator) instead of `start_urls` when you need headers, methods or custom callbacks.

## Request

```python
Request(url, method="GET", headers={}, callback=None, errback=None, meta={}, priority=0,
        dont_filter=False, max_retries=None, retry_delay=None)
```

`callback`/`errback` accept a callable or a method **name**. `request.replace(...)` copies with changes. Retries are executed by the client; the spider passes the numbers down.

## Settings

Class attributes, or constructor kwargs (unknown names raise `TypeError`):

| Setting | Default | Meaning |
| --- | --- | --- |
| `name` | `"spider"` | Logger name `xcrap.spider.<name>` |
| `start_urls` | `[]` | Initial URLs |
| `headers` | `{}` | Sent with every request |
| `concurrency` | `8` | Requests in flight |
| `request_delay` | `0` | Minimum ms between request starts (all workers) |
| `max_retries` / `retry_delay` | `0` / `0` | Per-request retry policy |
| `max_requests` | `None` | Stop scheduling after N |
| `max_depth` | `None` | Do not follow deeper than N |
| `dedupe` | `True` | Skip URLs already scheduled (method + URL without fragment, sorted query) |

```python
BooksSpider(concurrency=2, request_delay=500, max_requests=100).run()
```

## Pipelines

```python
class RequireTitle(ItemPipeline):
    async def open_spider(self, spider): ...
    async def close_spider(self, spider): ...

    async def process_item(self, item, spider):
        if not item["title"]:
            raise DropItem("empty title")          # counted in stats.items_dropped
        return item


memory = MemoryPipeline()
BooksSpider(pipelines=[RequireTitle(), memory, JsonLinesPipeline("books.jsonl")]).run()
memory.items
```

Pipelines run in order; each receives what the previous returned. Other exceptions are logged, counted in `stats.pipeline_errors`, and drop the item.

## Errors

| Event | Behavior |
| --- | --- |
| Non-2xx response | `errback`, or `Spider.on_error(response)`; `stats.requests_failed += 1` |
| Exception in a callback | logged, `stats.callback_errors += 1`, crawl continues |
| `DropItem` in a pipeline | item discarded |

```python
async def on_error(self, response):
    if response.status == 429:
        yield response.request.replace(dont_filter=True)
```

Lifecycle hooks: `async def on_open(self)` and `async def on_close(self)`. `spider.stats` has `requests_scheduled`, `requests_made`, `requests_failed`, `requests_filtered`, `requests_dropped`, `items_scraped`, `items_dropped`, `callback_errors`, `pipeline_errors`, `status_counts`, `elapsed`.

## ModelSpider

```python
class QuotesSpider(ModelSpider):
    start_urls = ["https://quotes.toscrape.com"]
    model = QuoteModel                           # HtmlExtractionModel
    items_query = css("div.quote")               # one item per match (omit: one item per page)
    follow_query = css("li.next a::attr(href)")  # links to follow with the same behavior
```

## Other clients

Any client works: `QuotesSpider(client=CurlCffiClient(impersonate="chrome120"))`. Spiders do not forward `actions=` to browser clients; subclass the client to set default actions. Rotation of user agents/proxies is configured on the client.

## Testing offline

Inject a fake client that serves canned pages:

```python
from xcrap.core import HttpClientBase, HttpResponse


class FakeClient(HttpClientBase):
    def __init__(self, pages):
        super().__init__()
        self.pages = pages

    async def fetch(self, url, method="GET", retries=0, max_retries=0, retry_delay=0, headers=None):
        if url not in self.pages:
            return HttpResponse(404, "Not Found", "", {})
        return HttpResponse(200, "OK", self.pages[url], {})

    async def fetch_many(self, requests, request_delay, concurrency):
        raise NotImplementedError


items = await BooksSpider(client=FakeClient({"https://books.toscrape.com": html})).collect()
```

## Coming from Scrapy

Downloader middlewares (retries, user agent, proxy) live in the **client**; `Response.css()` in callbacks becomes `response.as_html_parser()` + extraction models; items are `dict`s or pydantic models; settings are class attributes. There is no autothrottle, robots.txt handling, request bodies or persistent queue.

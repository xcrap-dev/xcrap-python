# Spiders

A **spider** crawls: it starts from some URLs, turns each response into *items* and *more requests*, and keeps going until nothing is left to visit. It takes care of the scheduler, de-duplication, throttling, concurrency, error handling and statistics, so your code only says *what a page means*.

Spiders are inspired by [Scrapy](https://scrapy.org) and adapted to Xcrap — see [Differences from Scrapy](#differences-from-scrapy).

```python
from xcrap.extractor import css
from xcrap.spiders import Spider


class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com"]
    concurrency = 4

    async def parse(self, response):
        parser = response.as_html_parser()

        for quote in parser.extract_models(QuoteModel, css("div.quote")):
            yield quote                                  # item

        for href in parser.extract_values(css("li.next a::attr(href)")):
            yield response.follow(href)                  # request
```

## Running a spider

| Call | Returns | Notes |
| --- | --- | --- |
| `spider.run()` | `SpiderStats` | Blocking (`asyncio.run`). For scripts |
| `await spider.crawl()` | `SpiderStats` | Inside async code. Items go to [pipelines](#item-pipelines) |
| `await spider.collect()` | `list` of items | Convenience: crawl and keep every item in memory |
| `async for item in spider.stream()` | items | Items arrive **while the crawl is running**; leaving the loop early cancels the crawl |

Constructor: `Spider(client=None, pipelines=None, **settings)`. Without a `client` an `HttpxClient` is created.

## What a callback may produce

A callback receives a [`SpiderResponse`](#spiderresponse) and may be a regular function, a coroutine, a generator or an async generator. Whatever it returns or yields is classified:

| Value | Treated as |
| --- | --- |
| `Request` | Scheduled for download |
| `dict`, pydantic `BaseModel`, any other object | An **item**, sent through the pipelines |
| `None` | Ignored |
| list / iterable / (async) generator of the above | Each element is classified |

```python
def parse_author(self, response):        # returning one item is fine
    return {"name": ...}

async def parse(self, response):         # so is yielding many things
    yield {"page": response.url}
    yield response.follow("/next")
```

An exception in a callback is logged and counted (`stats.callback_errors`); the crawl continues.

## Starting points

Either set `start_urls`, or override `start_requests()` (sync or async generator) when you need headers, methods or custom callbacks:

```python
class ApiSpider(Spider):
    async def start_requests(self):
        for page in range(1, 6):
            yield Request(f"https://api.example.com/items?page={page}", headers={"Accept": "application/json"})
```

Pair it with [`StaticPaginator`](utilities.md#staticpaginator) to generate numbered pages: `start_urls = paginator.dump()`.

## Request

```python
Request(
    url,
    method="GET",
    headers={},            # merged over the spider's `headers`
    callback=None,         # callable or *name* of a spider method; default: spider.parse
    errback=None,          # same, called for non-2xx responses
    meta={},               # free-form data carried to the response (response.meta)
    priority=0,            # higher is scheduled first
    dont_filter=False,     # True bypasses duplicate filtering
    max_retries=None,      # None -> spider.max_retries
    retry_delay=None,      # ms; None -> spider.retry_delay
)
```

`request.replace(url=...)` returns a modified copy. `request.depth` is filled in by the spider (start requests are depth 0; a request yielded from a callback is its parent's depth + 1).

Retries are executed by the **client** (see [Clients](clients.md#failures-do-not-raise)); the spider just passes the numbers down.

## SpiderResponse

An `HttpResponse` (so every member from [Clients → HttpResponse](clients.md#httpresponse) works) plus:

| Member | Description |
| --- | --- |
| `request`, `url`, `meta` | The originating request, its URL and its `meta` |
| `urljoin(url)` | Resolve a relative URL against this page |
| `follow(url, callback=None, **kwargs)` | Build a `Request` for a relative/absolute URL. `callback` defaults to **the callback that produced this response**; other keyword arguments go to `Request` (`meta`, `priority`, `errback`…) |
| `follow_all(urls, ...)` | List of `follow()` requests |

```python
yield response.follow(href, callback="parse_book", meta={"category": category}, priority=10)
```

and later `response.meta["category"]`.

## Settings

Set them as class attributes, or per instance as keyword arguments — an unknown name raises `TypeError`.

| Setting | Default | Meaning |
| --- | --- | --- |
| `name` | `"spider"` | Used in the logger name (`xcrap.spider.<name>`) |
| `start_urls` | `[]` | Initial URLs |
| `headers` | `{}` | Sent with every request |
| `concurrency` | `8` | Requests in flight at once |
| `request_delay` | `0` | Minimum ms between request **starts**, across all workers |
| `max_retries` / `retry_delay` | `0` / `0` | Per-request retry policy (ms for the delay) |
| `max_requests` | `None` | Stop scheduling after N requests |
| `max_depth` | `None` | Do not follow links deeper than N |
| `dedupe` | `True` | Skip URLs already scheduled |

```python
spider = BooksSpider(concurrency=2, request_delay=500, max_requests=100)
```

### De-duplication

A URL is considered seen by `METHOD + scheme + host + path + sorted query string`; the `#fragment` is ignored, so `?b=2&a=1` and `?a=1&b=2` are the same request. Skipped requests are counted in `stats.requests_filtered`. Pass `dont_filter=True` on a `Request` to revisit a URL deliberately.

### Limits

`max_requests` and `max_depth` stop **scheduling**, not in-flight work: requests already queued still complete. Refused requests are counted in `stats.requests_dropped`.

## Item pipelines

Pipelines post-process items in order; each receives what the previous one returned. Subclass `ItemPipeline`:

```python
from xcrap.spiders import DropItem, ItemPipeline, JsonLinesPipeline, MemoryPipeline


class RequireText(ItemPipeline):
    async def open_spider(self, spider): ...             # optional
    async def close_spider(self, spider): ...            # optional

    async def process_item(self, item, spider):
        if not item["text"]:
            raise DropItem("empty text")                  # counted in stats.items_dropped
        return item


memory = MemoryPipeline()
QuotesSpider(pipelines=[RequireText(), memory, JsonLinesPipeline("quotes.jsonl")]).run()
memory.items
```

Built in: `MemoryPipeline` (keeps `items`) and `JsonLinesPipeline(path)` (one JSON document per line; pydantic items are dumped with `model_dump()`). Any other exception inside a pipeline is logged, counted in `stats.pipeline_errors`, and drops that item.

Complete example: [`examples/21_spider_pipelines.py`](../examples/21_spider_pipelines.py).

## Errors

| What happened | What the spider does |
| --- | --- |
| Non-2xx response | Calls the request's `errback`, or `Spider.on_error(response)` if none. Counted in `stats.requests_failed`. Both may yield requests/items |
| Exception in a callback | Logged with traceback, `stats.callback_errors += 1`, crawl continues |
| Exception from the client itself | Logged, `requests_failed += 1` |
| `DropItem` | Item discarded quietly |

```python
async def on_error(self, response):
    if response.status == 429:
        yield response.request.replace(dont_filter=True)     # try again later
```

(The default `on_error` just logs a warning.)

## Lifecycle hooks

`async def on_open(self)` runs before the first request and `async def on_close(self)` after the crawl ends (also on failure). Pipelines' `open_spider` / `close_spider` run around them.

## Statistics

`spider.stats` (also the return value of `crawl()` / `run()`):

| Field | Meaning |
| --- | --- |
| `requests_scheduled` | Accepted by the scheduler |
| `requests_made` | Responses received |
| `requests_failed` | Non-2xx or client errors |
| `requests_filtered` | Skipped as duplicates |
| `requests_dropped` | Refused by `max_requests` / `max_depth` |
| `items_scraped` / `items_dropped` | Items that completed / were dropped by the pipelines |
| `callback_errors`, `pipeline_errors` | Exceptions swallowed so the crawl could go on |
| `status_counts` | `{status: count}` |
| `elapsed` | Seconds since the crawl started |

## ModelSpider: no `parse` to write

For the common "extract the same model from every page and follow the pagination" case, declare it:

```python
from xcrap.spiders import ModelSpider


class QuotesSpider(ModelSpider):
    start_urls = ["https://quotes.toscrape.com"]
    model = QuoteModel                           # an HtmlExtractionModel
    items_query = css("div.quote")               # one item per match (omit for one item per page)
    follow_query = css("li.next a::attr(href)")  # links to follow with the same behaviour
```

Runnable: [`examples/22_spider_declarative.py`](../examples/22_spider_declarative.py). When a site needs more than that, subclass `Spider` instead — the two are interchangeable.

## Using other clients

A spider calls `client.fetch(...)` for each request, so any [client](clients.md) works:

```python
from xcrap.clients import CurlCffiClient

QuotesSpider(client=CurlCffiClient(impersonate="chrome120"))
```

Spiders do not pass `actions=` to browser clients. Subclass the client and set them as defaults:

```python
class WaitForQuotes(PlaywrightClient):
    async def fetch(self, *args, **kwargs):
        kwargs.setdefault("actions", [lambda page: page.wait_for_selector("div.quote")])
        return await super().fetch(*args, **kwargs)

JsQuotesSpider(client=WaitForQuotes(), concurrency=1)
```

See [`examples/25_spider_playwright.py`](../examples/25_spider_playwright.py). Rotating user agents and proxies is also done in the client ([Clients → User agents and proxies](clients.md#user-agents-and-proxies)).

## Testing a spider offline

Because the client is injected, tests need no network: write a client that serves canned pages.

```python
class FakeClient(HttpClientBase):
    def __init__(self, pages): super().__init__(); self.pages = pages

    async def fetch(self, url, method="GET", retries=0, max_retries=0, retry_delay=0, headers=None):
        if url not in self.pages:
            return HttpResponse(404, "Not Found", "", {})
        return HttpResponse(200, "OK", self.pages[url], {})

    async def fetch_many(self, requests, request_delay, concurrency): raise NotImplementedError


items = await MySpider(client=FakeClient({"https://site.test/": "<html>…</html>"})).collect()
```

The framework's own tests (`tests/spiders/test_spider.py`) use exactly this.

## Differences from Scrapy

If you know Scrapy, this is the translation table.

| Scrapy | Xcrap | Why |
| --- | --- | --- |
| Twisted reactor, `scrapy crawl` | `asyncio`; `spider.run()` / `await spider.crawl()` | Plays well with the rest of async Python; no project scaffolding or CLI |
| `scrapy.Request`, `response.follow` | `xcrap.spiders.Request`, `response.follow` | Same idea |
| `Response.css()` / `.xpath()` in callbacks | `response.as_html_parser()` plus declarative **extraction models** | Xcrap's core idea: describe the shape once, reuse it in spiders, scripts and factories |
| Downloader middlewares (retry, user agent, proxy, cookies, redirects) | The **client** does it: `max_retries`, rotating `user_agent`/`proxy_url` callables, impersonation, browsers | One place for transport concerns; swap clients instead of stacking middlewares |
| Item classes / `scrapy.Item` | `dict` or pydantic `BaseModel` | No extra type to learn |
| Item pipelines | `ItemPipeline`, `DropItem` | Same, async by default |
| Feed exports (`-o items.json`) | `JsonLinesPipeline`, `MemoryPipeline`, or `stream()` | Write your own pipeline for other formats |
| Settings module | Class attributes / constructor kwargs | Per-spider, explicit |
| Signals, extensions | `on_open` / `on_close` / `on_error` hooks | Smaller surface |
| `Spider.start()` | `start_requests()` (sync or async generator) | |
| Item loaders | Extraction models with `extractor=` functions | |
| `CrawlSpider` with rules | `ModelSpider` (`items_query` + `follow_query`) or `response.follow` in `parse` | |
| Scrapy-Playwright | `PlaywrightClient` is a first-class client | |
| Autothrottle, robots.txt, persistent job queue, request bodies | Not provided (yet) | Use `request_delay`/`concurrency`; the queue lives in memory for one `crawl()` |

Things worth knowing: one `crawl()` runs at a time per spider instance; its scheduler and statistics reset on every call; `HttpxClient` keeps one session per client, so cookies persist across a crawl, while browser clients start every request from a clean browser.

## Examples

| File | Shows |
| --- | --- |
| [`20_spider_callbacks.py`](../examples/20_spider_callbacks.py) | Callbacks, `follow`, settings, stats |
| [`21_spider_pipelines.py`](../examples/21_spider_pipelines.py) | Pipelines, pydantic items, JSON Lines export |
| [`22_spider_declarative.py`](../examples/22_spider_declarative.py) | `ModelSpider` and `stream()` |
| [`23_spider_json_api.py`](../examples/23_spider_json_api.py) | Crawling a JSON API |
| [`24_spider_list_detail.py`](../examples/24_spider_list_detail.py) | List → detail pages, `meta`, `priority`, `errback` |
| [`25_spider_playwright.py`](../examples/25_spider_playwright.py) | A spider on a browser client |

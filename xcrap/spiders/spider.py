import asyncio
import inspect
import logging
import time
from typing import Any, AsyncIterator, Awaitable, Callable, ClassVar, Optional

from pydantic import BaseModel

from ..clients.httpx import HttpxClient
from ..core.errors import DropItem
from ..core.http_client_base import HttpClientBase
from ..extractor.html_extraction_model import HtmlExtractionModel
from ..extractor.query_builders import QueryConfig
from .pipelines import ItemPipeline
from .request import Callback, Request
from .response import SpiderResponse
from .scheduler import Scheduler
from .stats import SpiderStats


async def _flatten(result: Any) -> AsyncIterator[Any]:
    """Normalizes anything a callback may return (coroutine, (async) generator, list, single value, None)."""
    if inspect.isawaitable(result):
        result = await result

    if result is None:
        return

    if inspect.isasyncgen(result):
        async for entry in result:
            yield entry
    elif isinstance(result, (dict, BaseModel, Request, str, bytes)) or not hasattr(result, "__iter__"):
        yield result
    else:
        for entry in result:
            yield entry


class Spider:
    """
    A crawler described by its start URLs and callbacks.

    Callbacks receive a `SpiderResponse` and yield `Request`s (to keep crawling) and/or items
    (dicts or pydantic models). Fetching, retries, proxies and user agents are delegated to the
    `client`, so there are no download middlewares: pick or build a client instead.

    Delays (`request_delay`, `retry_delay`) are in milliseconds, like the rest of Xcrap.
    """

    name: ClassVar[str] = "spider"
    start_urls: ClassVar[list[str]] = []
    headers: ClassVar[dict[str, str]] = {}
    concurrency: ClassVar[int] = 8
    request_delay: ClassVar[int] = 0
    max_retries: ClassVar[int] = 0
    retry_delay: ClassVar[int] = 0
    max_requests: ClassVar[Optional[int]] = None
    max_depth: ClassVar[Optional[int]] = None
    dedupe: ClassVar[bool] = True

    def __init__(
        self,
        client: Optional[HttpClientBase] = None,
        pipelines: Optional[list[ItemPipeline]] = None,
        **settings: Any,
    ) -> None:
        for key, value in settings.items():
            if key in ("client", "pipelines") or not hasattr(type(self), key):
                raise TypeError(f"Unknown spider setting: {key!r}")

            setattr(self, key, value)

        self.client = client or HttpxClient()
        self.pipelines = list(pipelines or [])
        self.logger = logging.getLogger(f"xcrap.spider.{self.name}")
        self.stats = SpiderStats()
        self._sink: Optional[Callable[[Any], Awaitable[None]]] = None

    # ---- user API -------------------------------------------------------------------------------------------

    async def start_requests(self) -> AsyncIterator[Request]:
        for url in self.start_urls:
            yield Request(url=url)

    async def parse(self, response: SpiderResponse) -> Any:
        raise NotImplementedError(f"{type(self).__name__}.parse() must be implemented.")

    async def on_open(self) -> None:
        pass

    async def on_close(self) -> None:
        pass

    async def on_error(self, response: SpiderResponse) -> Any:
        """Called for non-2xx responses of requests without an `errback`. May yield requests/items."""
        self.logger.warning("%s %s -> %s %s", response.request.method, response.url, response.status, response.status_text)

    # ---- running --------------------------------------------------------------------------------------------

    def run(self) -> SpiderStats:
        """Blocking entry point: `MySpider().run()`."""
        return asyncio.run(self.crawl())

    async def collect(self) -> list[Any]:
        return [item async for item in self.stream()]

    async def stream(self) -> AsyncIterator[Any]:
        """Runs the crawl in the background and yields items as soon as they are scraped."""
        queue: asyncio.Queue[Any] = asyncio.Queue()
        finished = object()
        self._sink = queue.put

        async def runner() -> None:
            try:
                await self.crawl()
            finally:
                await queue.put(finished)

        task = asyncio.create_task(runner())

        try:
            while (item := await queue.get()) is not finished:
                yield item

            await task
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            self._sink = None

    async def crawl(self) -> SpiderStats:
        self.stats = SpiderStats()
        self._scheduler = Scheduler(dedupe=self.dedupe)
        self._throttle_lock = asyncio.Lock()
        self._next_slot = 0.0
        workers: list[asyncio.Task] = []

        for pipeline in self.pipelines:
            await pipeline.open_spider(self)

        try:
            await self.on_open()

            async for request in _flatten(self.start_requests()):
                self._schedule(request, parent=None)

            workers = [asyncio.create_task(self._worker()) for _ in range(max(1, self.concurrency))]
            await self._scheduler.join()
        finally:
            for worker in workers:
                worker.cancel()

            await asyncio.gather(*workers, return_exceptions=True)
            await self.on_close()

            for pipeline in self.pipelines:
                await pipeline.close_spider(self)

            self.stats.finished_at = time.time()

        return self.stats

    # ---- internals ------------------------------------------------------------------------------------------

    def _schedule(self, request: Request, parent: Optional[Request]) -> None:
        if request.depth is None:
            request.depth = 0 if parent is None else (parent.depth or 0) + 1

        if self.max_depth is not None and request.depth > self.max_depth:
            self.stats.requests_dropped += 1
            return

        if self.max_requests is not None and self.stats.requests_scheduled >= self.max_requests:
            self.stats.requests_dropped += 1
            return

        if self._scheduler.is_duplicate(request):
            self.stats.requests_filtered += 1
            return

        self.stats.requests_scheduled += 1
        self._scheduler.push(request)

    async def _worker(self) -> None:
        while True:
            request = await self._scheduler.pop()

            try:
                await self._process(request)
            except Exception:
                self.stats.requests_failed += 1
                self.logger.exception("Unhandled error while processing %s", request.url)
            finally:
                self._scheduler.done()

    async def _throttle(self) -> None:
        if not self.request_delay:
            return

        async with self._throttle_lock:
            loop = asyncio.get_running_loop()
            slot = max(loop.time(), self._next_slot)
            self._next_slot = slot + self.request_delay / 1000
            await asyncio.sleep(max(0.0, slot - loop.time()))

    async def _process(self, request: Request) -> None:
        await self._throttle()

        http_response = await self.client.fetch(
            url=request.url,
            method=request.method,
            max_retries=request.max_retries if request.max_retries is not None else self.max_retries,
            retry_delay=request.retry_delay if request.retry_delay is not None else self.retry_delay,
            headers={**self.headers, **request.headers} or None,
        )
        response = SpiderResponse.from_http(http_response, request)

        self.stats.requests_made += 1
        self.stats.status_counts[response.status] = self.stats.status_counts.get(response.status, 0) + 1

        if response.is_success():
            handler = self._resolve(request.callback) or self.parse
        else:
            self.stats.requests_failed += 1
            handler = self._resolve(request.errback) or self.on_error

        try:
            await self._handle_output(handler(response), request)
        except Exception:
            self.stats.callback_errors += 1
            self.logger.exception("Error in %s for %s", getattr(handler, "__name__", handler), request.url)

    def _resolve(self, callback: Optional[Callback]) -> Optional[Callable[..., Any]]:
        return getattr(self, callback) if isinstance(callback, str) else callback

    async def _handle_output(self, result: Any, parent: Request) -> None:
        async for output in _flatten(result):
            if isinstance(output, Request):
                self._schedule(output, parent)
            else:
                await self._emit(output)

    async def _emit(self, item: Any) -> None:
        try:
            for pipeline in self.pipelines:
                item = await pipeline.process_item(item, self)
        except DropItem as drop:
            self.stats.items_dropped += 1
            self.logger.debug("Item dropped: %s", drop.reason)
            return
        except Exception:
            self.stats.pipeline_errors += 1
            self.logger.exception("Pipeline error")
            return

        self.stats.items_scraped += 1

        if self._sink:
            await self._sink(item)


class ModelSpider(Spider):
    """
    Declarative spider: no `parse` to write. Extracts `model` from every page, once per element
    matched by `items_query` when given, and follows every link matched by `follow_query`.
    """

    model: ClassVar[type[HtmlExtractionModel]]
    items_query: ClassVar[Optional[QueryConfig]] = None
    follow_query: ClassVar[Optional[QueryConfig]] = None

    async def parse(self, response: SpiderResponse) -> Any:
        parser = response.as_html_parser()

        if self.items_query:
            items = parser.extract_models(self.model, self.items_query)
        else:
            items = [parser.extract_model(self.model)]

        for item in items:
            yield item

        if self.follow_query:
            for href in parser.extract_values(self.follow_query):
                yield response.follow(href)


__all__ = ["Spider", "ModelSpider"]

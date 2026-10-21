import pytest

from xcrap.core import HttpResponse
from xcrap.extractor import HtmlBaseField, HtmlExtractionModel, css
from xcrap.spiders import ItemPipeline, ModelSpider, Request, Scheduler, Spider, SpiderResponse
from xcrap.spiders.spider import _flatten

from .test_spider import PAGES, FakeClient


class ListSpider(Spider):
    start_urls = ["http://site.test/detail"]

    async def parse(self, response):
        # A coroutine returning a plain list: awaited, then each entry is classified.
        return [{"a": 1}, Request("http://site.test/p2", callback="second"), None]

    def second(self, response):
        return iter([{"b": 2}])


async def test_callbacks_may_return_lists_and_iterators():
    items = await ListSpider(client=FakeClient(PAGES)).collect()

    assert items == [{"a": 1}, {"b": 2}] or items == [{"b": 2}, {"a": 1}]


async def test_flatten_handles_awaitables_and_generators():
    async def coroutine():
        return {"x": 1}

    assert [entry async for entry in _flatten(coroutine())] == [{"x": 1}]
    assert [entry async for entry in _flatten(None)] == []
    assert [entry async for entry in _flatten("text")] == ["text"]


async def test_base_parse_must_be_implemented_and_failure_is_counted():
    class Bare(Spider):
        start_urls = ["http://site.test/detail"]

    spider = Bare(client=FakeClient(PAGES))
    await spider.crawl()

    assert spider.stats.callback_errors == 1


async def test_default_on_error_logs_a_warning(caplog):
    class S(Spider):
        start_urls = ["http://site.test/missing"]

    with caplog.at_level("WARNING"):
        await S(client=FakeClient(PAGES)).crawl()

    assert "404" in caplog.text


def test_run_is_a_blocking_entry_point():
    class S(Spider):
        start_urls = ["http://site.test/detail"]

        def parse(self, response):
            return {"ok": True}

    stats = S(client=FakeClient(PAGES)).run()

    assert stats.items_scraped == 1


async def test_client_exceptions_are_counted_and_do_not_stop_the_crawl():
    class Exploding(FakeClient):
        async def fetch(self, url, **kwargs):
            if url.endswith("/p2"):
                raise RuntimeError("network down")

            return await super().fetch(url, **kwargs)

    class S(Spider):
        start_urls = ["http://site.test/detail", "http://site.test/p2"]

        def parse(self, response):
            return {"ok": True}

    spider = S(client=Exploding(PAGES))
    await spider.crawl()

    assert spider.stats.items_scraped == 1
    assert spider.stats.requests_failed == 1


async def test_pipeline_errors_drop_the_item_and_are_counted():
    class Broken(ItemPipeline):
        async def process_item(self, item, spider):
            raise ValueError("bad pipeline")

    class S(Spider):
        start_urls = ["http://site.test/detail"]

        def parse(self, response):
            return {"ok": True}

    spider = S(client=FakeClient(PAGES), pipelines=[Broken()])
    await spider.crawl()

    assert spider.stats.pipeline_errors == 1
    assert spider.stats.items_scraped == 0


async def test_base_pipeline_passes_items_through():
    item = {"a": 1}

    assert await ItemPipeline().process_item(item, None) is item


async def test_model_spider_with_items_query():
    class Value(HtmlExtractionModel):
        v = HtmlBaseField(query=css("b.v::text"))

    class S(ModelSpider):
        start_urls = ["http://site.test/"]
        model = Value
        items_query = css("b.v")

    items = await S(client=FakeClient(PAGES)).collect()

    assert items == [{"v": "1"}]


def test_request_replace_and_response_helpers():
    request = Request("http://site.test/a", meta={"k": "v"}, callback="parse")
    copy = request.replace(url="http://site.test/b")

    assert copy.url == "http://site.test/b"
    assert copy.meta == {"k": "v"}

    response = SpiderResponse.from_http(HttpResponse(200, "OK", "", {}), request)

    assert response.meta == {"k": "v"}
    assert response.urljoin("/x") == "http://site.test/x"

    followed = response.follow_all(["/1", "/2"], priority=5)

    assert [r.url for r in followed] == ["http://site.test/1", "http://site.test/2"]
    assert all(r.callback == "parse" and r.priority == 5 for r in followed)


def test_scheduler_does_not_filter_when_disabled_or_dont_filter():
    request = Request("http://site.test/a")

    off = Scheduler(dedupe=False)
    off.push(request)
    assert off.is_duplicate(request) is False

    on = Scheduler()
    on.push(request)
    assert on.is_duplicate(request) is True
    assert on.is_duplicate(request.replace(dont_filter=True)) is False


@pytest.mark.asyncio
async def test_scheduler_pops_by_priority_then_insertion_order():
    scheduler = Scheduler()
    scheduler.push(Request("http://site.test/low"))
    scheduler.push(Request("http://site.test/high", priority=5))

    assert (await scheduler.pop()).url.endswith("/high")
    assert (await scheduler.pop()).url.endswith("/low")

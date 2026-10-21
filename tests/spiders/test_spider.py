import json

import pytest

from xcrap.core import HttpClientBase, HttpResponse
from xcrap.extractor import HtmlBaseField, HtmlExtractionModel, css
from xcrap.spiders import DropItem, ItemPipeline, JsonLinesPipeline, MemoryPipeline, ModelSpider, Request, Spider
from xcrap.spiders.scheduler import fingerprint


class FakeClient(HttpClientBase):
    def __init__(self, pages: dict[str, str]) -> None:
        super().__init__()
        self.pages = pages
        self.calls: list[dict] = []

    async def fetch(self, url, method="GET", retries=0, max_retries=0, retry_delay=0, headers=None):
        self.calls.append({"url": url, "max_retries": max_retries, "headers": headers})

        if url not in self.pages:
            return HttpResponse(404, "Not Found", "", {})

        return HttpResponse(200, "OK", self.pages[url], {})

    async def fetch_many(self, requests, request_delay, concurrency):
        raise NotImplementedError


PAGES = {
    "http://site.test/": '<a class="n" href="/p2">next</a><b class="v">1</b><a class="d" href="/detail">d</a>',
    "http://site.test/p2": '<a class="n" href="/">back</a><b class="v">2</b>',
    "http://site.test/detail": '<b class="v">detail</b>',
}


class ChainSpider(Spider):
    name = "chain"
    start_urls = ["http://site.test/"]

    async def parse(self, response):
        parser = response.as_html_parser()
        yield {"v": parser.extract_value(css("b.v::text")), "depth": response.request.depth}

        for href in parser.extract_values(css("a.n::attr(href)")):
            yield response.follow(href)

        for href in parser.extract_values(css("a.d::attr(href)")):
            yield response.follow(href, callback="parse_detail")

    def parse_detail(self, response):
        return {"detail": response.as_html_parser().extract_value(css("b.v::text"))}


async def test_follows_links_dedupes_and_collects_items():
    spider = ChainSpider(client=FakeClient(PAGES))
    items = await spider.collect()

    assert sorted(map(str, items)) == sorted(map(str, [{"v": "1", "depth": 0}, {"v": "2", "depth": 1}, {"detail": "detail"}]))
    assert spider.stats.requests_made == 3
    assert spider.stats.requests_filtered == 1  # p2 links back to "/"
    assert spider.stats.items_scraped == 3


async def test_max_depth_and_max_requests():
    shallow = ChainSpider(client=FakeClient(PAGES), max_depth=0)
    await shallow.crawl()
    assert shallow.stats.requests_made == 1

    capped = ChainSpider(client=FakeClient(PAGES), max_requests=2)
    await capped.crawl()
    assert capped.stats.requests_made == 2


async def test_failed_response_goes_to_errback():
    seen = []

    class S(Spider):
        async def start_requests(self):
            yield Request("http://site.test/missing", errback="failed")

        def failed(self, response):
            seen.append(response.status)

    spider = S(client=FakeClient(PAGES))
    await spider.crawl()

    assert seen == [404]
    assert spider.stats.requests_failed == 1


async def test_callback_error_does_not_stop_the_crawl():
    class S(ChainSpider):
        def parse_detail(self, response):
            raise RuntimeError("boom")

    spider = S(client=FakeClient(PAGES))
    await spider.crawl()

    assert spider.stats.callback_errors == 1
    assert spider.stats.items_scraped == 2


async def test_pipelines_drop_and_export(tmp_path):
    class DropDetail(ItemPipeline):
        async def process_item(self, item, spider):
            if "detail" in item:
                raise DropItem("no details")
            return item

    memory = MemoryPipeline()
    path = tmp_path / "out.jsonl"
    spider = ChainSpider(client=FakeClient(PAGES), pipelines=[DropDetail(), memory, JsonLinesPipeline(str(path))])
    await spider.crawl()

    assert len(memory.items) == 2
    assert spider.stats.items_dropped == 1
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2
    assert json.loads(path.read_text(encoding="utf-8").splitlines()[0])["v"] in ("1", "2")


async def test_settings_and_headers_reach_the_client():
    client = FakeClient(PAGES)

    class S(Spider):
        start_urls = ["http://site.test/detail"]
        headers = {"X-A": "1"}
        max_retries = 3

        def parse(self, response):
            return None

    await S(client=client).crawl()
    assert client.calls[0]["max_retries"] == 3
    assert client.calls[0]["headers"] == {"X-A": "1"}

    with pytest.raises(TypeError):
        S(client=client, nope=1)


async def test_request_delay_spaces_requests():
    spider = ChainSpider(client=FakeClient(PAGES), request_delay=50, concurrency=4)
    stats = await spider.crawl()

    assert stats.elapsed >= 0.08  # 3 requests -> at least 2 gaps of 50ms (with timer tolerance on Windows)


async def test_model_spider():
    class Value(HtmlExtractionModel):
        v = HtmlBaseField(query=css("b.v::text"))

    class S(ModelSpider):
        start_urls = ["http://site.test/"]
        model = Value
        follow_query = css("a.n::attr(href)")

    items = await S(client=FakeClient(PAGES)).collect()
    assert [i["v"] for i in items] == ["1", "2"]


def test_fingerprint_ignores_fragment_and_query_order():
    a = fingerprint(Request("http://x.test/p?b=2&a=1#top"))
    b = fingerprint(Request("http://X.test/p?a=1&b=2"))
    assert a == b


async def test_fake_client_does_not_support_fetch_many():
    with pytest.raises(NotImplementedError):
        await FakeClient(PAGES).fetch_many([], None, None)

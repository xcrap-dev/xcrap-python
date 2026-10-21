from unittest.mock import AsyncMock

import pytest

from xcrap.core.errors import InvalidPageValueError, PageParsingFailureError
from xcrap.core.http_response import HttpResponse
from xcrap.extractor.query_builders import css
from xcrap.utils.static_paginator import StaticPaginator

HTML = '<span class="cur">Page 3</span><span class="last">no digits</span><span class="n">12</span>'
TEMPLATE = "https://example.com/{page}"


def client_with(html=HTML):
    client = AsyncMock()
    client.fetch.return_value = HttpResponse(200, "OK", html, {})

    return client


async def track(trackers, request="https://example.com/1", client=None):
    return await StaticPaginator.create_with_tracking(
        client=client or client_with(),
        request=request,
        template_url=TEMPLATE,
        trackers=trackers,
    )


CURRENT = {"query": css("span.cur")}
LAST = {"query": css("span.n")}


async def test_request_may_be_a_dict_or_any_object():
    client = client_with()

    await track({"current_page": CURRENT, "last_page": LAST}, request={"url": "https://example.com/1"}, client=client)
    client.fetch.assert_awaited_with(url="https://example.com/1")

    await track({"current_page": CURRENT, "last_page": LAST}, request=("custom",), client=client)
    client.fetch.assert_awaited_with(("custom",))


async def test_tracker_without_query_fails():
    with pytest.raises(PageParsingFailureError, match="query is missing"):
        await track({"current_page": {}, "last_page": LAST})


async def test_extractor_returning_none_fails():
    with pytest.raises(PageParsingFailureError, match="None"):
        await track({"current_page": {**CURRENT, "extractor": lambda el: None}, "last_page": LAST})


async def test_failing_transformer_is_reported():
    def boom(raw):
        raise ValueError("nope")

    with pytest.raises(InvalidPageValueError, match="Transformer failed"):
        await track({"current_page": {**CURRENT, "transformer": boom}, "last_page": LAST})


async def test_numeric_extractor_result_is_used_directly():
    tracked = await track(
        {"current_page": {**CURRENT, "extractor": lambda el: 7.0}, "last_page": {**LAST, "extractor": lambda el: 9}}
    )

    assert tracked["paginator"].initial_page == 7
    assert tracked["paginator"].last_page == 9


async def test_value_without_digits_fails():
    with pytest.raises(InvalidPageValueError, match="Could not parse"):
        await track({"current_page": {"query": css("span.last"), "extractor": lambda el: el.css("::text").get()}, "last_page": LAST})

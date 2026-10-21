from unittest.mock import AsyncMock

import pytest

from xcrap.core.errors import (
    InvalidUrlError,
    PageOutOfRangeError,
    PageParsingFailureError,
)
from xcrap.core.http_response import HttpResponse
from xcrap.extractor.query_builders import css
from xcrap.utils.static_paginator import StaticPaginator, Trackers


def test_paginator_generate_url():
    url = StaticPaginator.generate_url("https://example.com/items?page={page}", 2)
    assert url == "https://example.com/items?page=2"


def test_paginator_invalid_url_raises_error():
    with pytest.raises(InvalidUrlError) as exc_info:
        StaticPaginator.generate_url("https://example.com/items?page=1", 2)
    assert "does not contain the placeholder '{page}'" in str(exc_info.value)


def test_paginator_initialization():
    paginator = StaticPaginator(
        initial_page=1,
        last_page=5,
        template_url="https://example.com?p={page}",
    )
    assert paginator.current_page == 1
    assert paginator.current == "https://example.com?p=1"


def test_paginator_next_and_previous():
    paginator = StaticPaginator(
        initial_page=2,
        last_page=4,
        min_page=1,
        template_url="https://example.com?p={page}",
    )

    assert paginator.next() == "https://example.com?p=3"
    assert paginator.next() == "https://example.com?p=4"

    # Out of range next
    with pytest.raises(PageOutOfRangeError):
        paginator.next()

    assert paginator.previous() == "https://example.com?p=3"
    assert paginator.previous() == "https://example.com?p=2"
    assert paginator.previous() == "https://example.com?p=1"

    # Out of range previous
    with pytest.raises(PageOutOfRangeError):
        paginator.previous()


def test_paginator_set():
    paginator = StaticPaginator(
        initial_page=1,
        last_page=5,
        template_url="https://example.com?p={page}",
    )
    assert paginator.set(3) == "https://example.com?p=3"
    assert paginator.current == "https://example.com?p=3"

    with pytest.raises(PageOutOfRangeError):
        paginator.set(10)

    with pytest.raises(PageOutOfRangeError):
        paginator.set(0)


def test_paginator_dump():
    paginator = StaticPaginator(
        initial_page=1,
        last_page=4,
        template_url="https://example.com?p={page}",
    )
    urls = paginator.dump()
    assert urls == [
        "https://example.com?p=1",
        "https://example.com?p=2",
        "https://example.com?p=3",
        "https://example.com?p=4",
    ]

    limited_urls = paginator.dump(limit=2)
    assert limited_urls == [
        "https://example.com?p=1",
        "https://example.com?p=2",
    ]


@pytest.mark.asyncio
async def test_paginator_create_with_tracking():
    mock_html = """
    <html>
        <body>
            <span class="current">2</span>
            <span class="total">Page 10 of 10</span>
        </body>
    </html>
    """
    mock_client = AsyncMock()
    mock_client.fetch.return_value = HttpResponse(
        status=200,
        status_text="OK",
        body=mock_html,
        headers={},
    )

    trackers: Trackers = {
        "current_page": {
            "query": css("span.current::text"),
        },
        "last_page": {
            "query": css("span.total::text"),
            "transformer": lambda val: 10,
        },
    }

    result = await StaticPaginator.create_with_tracking(
        client=mock_client,
        request="https://example.com/catalog",
        template_url="https://example.com/catalog?page={page}",
        trackers=trackers,
    )

    paginator = result["paginator"]
    assert paginator.initial_page == 2
    assert paginator.last_page == 10
    assert paginator.current == "https://example.com/catalog?page=2"


@pytest.mark.asyncio
async def test_paginator_create_with_tracking_failures():
    mock_client = AsyncMock()
    mock_client.fetch.return_value = HttpResponse(
        status=200,
        status_text="OK",
        body="<html><body>Empty</body></html>",
        headers={},
    )

    trackers: Trackers = {
        "current_page": {"query": css("span.not-found::text")},
        "last_page": {"query": css("span.not-found::text")},
    }

    with pytest.raises(PageParsingFailureError):
        await StaticPaginator.create_with_tracking(
            client=mock_client,
            request={"url": "https://example.com"},
            template_url="https://example.com?page={page}",
            trackers=trackers,
        )

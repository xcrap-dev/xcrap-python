"""
Many requests at once, plus static pagination (books.toscrape.com).

Shows: StaticPaginator.create_with_tracking (discovers current/last page from the HTML),
paginator.dump(), client.fetch_many with concurrency and request_delay, retries.

    poetry run python examples/10_fetch_many_and_pagination.py
"""

import asyncio
import re

from xcrap.clients import HttpxClient
from xcrap.extractor import css
from xcrap.utils import StaticPaginator

TEMPLATE_URL = "https://books.toscrape.com/catalogue/page-{page}.html"


async def main() -> None:
    client = HttpxClient()

    # "Page 1 of 50" -> current_page=1, last_page=50
    tracked = await StaticPaginator.create_with_tracking(
        client=client,
        request=TEMPLATE_URL.format(page=1),
        template_url=TEMPLATE_URL,
        trackers={
            "current_page": {"query": css("li.current")},
            "last_page": {"query": css("li.current"), "transformer": lambda raw: int(re.findall(r"\d+", raw)[-1])},
        },
    )
    paginator: StaticPaginator = tracked["paginator"]
    print(f"discovered {paginator.initial_page}..{paginator.last_page}")

    urls = paginator.dump(limit=6)
    responses = await client.fetch_many(
        [{"url": url, "method": "GET", "max_retries": 2, "retry_delay": 500} for url in urls],
        request_delay=100,  # ms between request starts
        concurrency=3,  # at most 3 in flight
    )

    for url, response in zip(urls, responses):
        titles = response.as_html_parser().extract_values(css("article.product_pod h3 a::attr(title)"))
        print(f"{response.status} {url.rsplit('/', 1)[-1]}: {len(titles)} books, first={titles[0]!r}")


if __name__ == "__main__":
    asyncio.run(main())

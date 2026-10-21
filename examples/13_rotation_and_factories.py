"""
Rotating user agents/proxies and building clients and models from plain configuration (httpbin.org, quotes.toscrape.com).

Shows: Rotator, Randomizer, callables as `user_agent`/`proxy_url`, create_client, create_extraction_model.

    poetry run python examples/13_rotation_and_factories.py
"""

import asyncio

from xcrap.clients import HttpxClient
from xcrap.extractor import HtmlExtractionModel
from xcrap.factory import create_client, create_extraction_model
from xcrap.utils import Randomizer, Rotator

AGENTS = Rotator(["xcrap-bot/1.0 (a)", "xcrap-bot/1.0 (b)", "xcrap-bot/1.0 (c)"])

# Anything JSON-serialisable can describe a model, so it can live in a file or a database.
MODEL_CONFIG = {
    "type": "html",
    "model": {
        "quotes": {
            "query": {"type": "css", "value": "div.quote"},
            "multiple": True,
            "limit": 3,
            "nested": {
                "type": "html",
                "model": {
                    "text": {"query": {"type": "css", "value": "span.text::text"}},
                    "author": {"query": {"type": "css", "value": "small.author::text"}},
                    "tags": {"query": {"type": "css", "value": "a.tag::text"}, "multiple": True},
                },
            },
        }
    },
}


async def main() -> None:
    # `user_agent` may be a callable: it is resolved on every request, so each one rotates.
    client = create_client(
        "httpx",
        allowed_clients={"httpx": HttpxClient},
        options={"user_agent": lambda: next(AGENTS)},
    )

    for _ in range(4):
        response = await client.fetch(url="https://httpbin.org/user-agent")
        print("rotator   :", response.json["user-agent"])

    random_client = HttpxClient(user_agent=lambda: Randomizer.user_agent("firefox"))
    print("randomizer:", (await random_client.fetch(url="https://httpbin.org/user-agent")).json["user-agent"])

    model = create_extraction_model(MODEL_CONFIG, allowed_models={"html": HtmlExtractionModel}, allowed_extractors={})
    page = await client.fetch(url="https://quotes.toscrape.com/")
    for quote in model.extract(page.text)["quotes"]:
        print(quote["author"], quote["tags"])


if __name__ == "__main__":
    asyncio.run(main())

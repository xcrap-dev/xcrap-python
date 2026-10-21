"""
Markdown inside a JSON API response (GitHub releases).

The `body` field of a release is Markdown text. JsonParser gets it out, MarkdownParser queries it.

    poetry run python examples/05_markdown_inside_json.py
"""

import asyncio

from xcrap.clients import HttpxClient
from xcrap.extractor import MarkdownParser, css, jmes_path


async def main() -> None:
    client = HttpxClient()
    response = await client.fetch(
        url="https://api.github.com/repos/psf/requests/releases/latest",
        headers={"Accept": "application/vnd.github+json"},
    )

    release = response.as_json_parser()
    print("release:", release.extract_value(jmes_path("name")), "-", release.extract_value(jmes_path("published_at")))

    notes = MarkdownParser(release.extract_value(jmes_path("body")))
    print("sections:", notes.extract_values(css("h2::text")))
    print("bullets:", len(notes.extract_values(css("li"))))
    print("first bullet (HTML):", notes.extract_value(css("li")))


if __name__ == "__main__":
    asyncio.run(main())

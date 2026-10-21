"""
The full chain: HTML -> <script type="application/json"> -> JSON -> Markdown.

A GitHub file page embeds the file source as a JSON list of lines (`rawLines`) in a script tag.
We query the HTML for the script, parse its JSON, join the lines back into Markdown and query that.

GitHub's embedded payload is an implementation detail and may change; the technique doesn't.

    poetry run python examples/06_markdown_in_json_in_script.py
"""

import asyncio

from xcrap.clients import HttpxClient
from xcrap.extractor import JsonParser, MarkdownParser, css, jmes_path


async def main() -> None:
    client = HttpxClient()
    response = await client.fetch(url="https://github.com/psf/requests/blob/main/README.md")

    # 1. HTML: find the script that carries the data
    script = response.as_html_parser().extract_value(css('script[data-target="react-app.embeddedData"]::text'))

    # 2. JSON: keys containing dots must be quoted in JMESPath
    lines = JsonParser(script).extract_value(jmes_path('payload."codeViewBlobLayoutRoute.StyledBlob".rawLines'))

    # 3. Markdown: the lines joined are the original README
    readme = MarkdownParser("\n".join(lines))

    print("title:", readme.extract_value(css("h1::text")))
    print("sections:", readme.extract_values(css("h2::text")))
    print("links:", readme.extract_values(css("a::attr(href)"), limit=3))


if __name__ == "__main__":
    asyncio.run(main())

"""
Bot-detection resistant browsing with SeleniumBaseClient (quotes.toscrape.com/js/ and bot.sannysoft.com).

SeleniumBase's UC mode drives a patched Chrome that hides the usual automation fingerprints. This script
loads a JavaScript-rendered page, then asks a public fingerprint test page how "automated" the browser looks.
Requires: pip install "xcrap[seleniumbase]"  (and Chrome installed)

    poetry run python examples/15_client_seleniumbase.py
"""

import asyncio

from xcrap.clients import SeleniumBaseClient
from xcrap.extractor import css


async def main() -> None:
    client = SeleniumBaseClient(headless=True, uc=True, reconnect_time=3.0)

    response = await client.fetch(url="https://quotes.toscrape.com/js/")
    parser = response.as_html_parser()
    print("rendered quotes:", len(parser.extract_values(css("div.quote"))))
    print("first author   :", parser.extract_value(css("small.author::text")))

    # Actions receive the SeleniumBase driver: run JS, click, or use its anti-bot helpers
    # (driver.uc_gui_click_captcha(), driver.uc_click(selector), ...).
    response = await client.fetch(
        url="https://bot.sannysoft.com/",
        actions=[lambda driver: driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")],
    )
    parser = response.as_html_parser()
    print("webdriver flag :", parser.extract_value(css("td#webdriver-result::text")))
    print("failed checks  :", len(parser.extract_values(css("td.failed"))))


if __name__ == "__main__":
    asyncio.run(main())

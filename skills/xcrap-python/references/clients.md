# Clients

```python
from xcrap.clients import CurlCffiClient, HttpxClient, PlaywrightClient, SeleniumBaseClient, SeleniumClient
```

All clients derive from `HttpClientBase`, implement `fetch()` / `fetch_many()` and return the same `HttpResponse`, so parsers, spiders and your own code never depend on which client is used.

## Choosing a client

Pick the lightest one that returns the data. Move down only when the one above fails.

| Client | Extra | Use it when |
| --- | --- | --- |
| `HttpxClient` | none | Default. Plain HTML/JSON, fastest, keeps one session (cookies persist). |
| `CurlCffiClient` | `curl` | The site blocks Python's TLS fingerprint (Cloudflare and similar). `impersonate="chrome120"`. |
| `PlaywrightClient` | `playwright` | Content rendered by JavaScript, or you must click/scroll/type. |
| `SeleniumClient` | `selenium` | You already depend on WebDriver. |
| `SeleniumBaseClient` | `seleniumbase` | Active automation detection (Turnstile, CAPTCHAs): UC (undetected) mode. |

Before using a browser, look for the data in the HTML (`<script id="__NEXT_DATA__">`, JSON-LD, inline state) or in a JSON endpoint the page calls (DevTools → Network). Fetching that with `HttpxClient` is faster and more stable.

## fetch

```python
client = HttpxClient()
response = await client.fetch(
    url="https://example.com/products",
    method="GET",            # ignored by browser clients (they navigate)
    max_retries=3,           # extra attempts after the first
    retry_delay=500,         # ms between attempts
    headers={"Accept-Language": "en"},
)
```

Browser clients also accept `actions=`; `PlaywrightClient` also accepts `wait_until=`.

## Failures do not raise

```python
if not response.is_success():
    print(response.status, response.status_text, response.attempts, response.failed_attempts)
```

| Client | Retries on | After the last attempt |
| --- | --- | --- |
| `HttpxClient` | exceptions **and** non-2xx | the real status/body of the failing response, or `500` with the error text |
| curl, Playwright, Selenium, SeleniumBase | exceptions only | a 404 page is returned as is; exceptions become `500` |

Selenium-based clients cannot read HTTP status codes or headers: they always report `200` for a rendered page. Validate the content (e.g. look for an expected element) instead of trusting the status.

## HttpResponse

| Member | Description |
| --- | --- |
| `status`, `status_text`, `is_success()` | Status; success means 2xx |
| `body` / `text`, `json` | Body as `str`; `json` is `json.loads(body)` |
| `headers`, `get_header(name)` | Lower-cased header dict, case-insensitive lookup |
| `attempts`, `failed_attempts` | Tries made and why earlier ones failed |
| `as_html_parser()`, `as_json_parser()`, `as_markdown_parser()` | Parsers over the body |
| `as_xml_parser(namespaces=None, remove_namespaces=False)` | `XmlParser` over the body |
| `as_parser(MyParser)` | Any `SourceParser` subclass |

## fetch_many

```python
responses = await client.fetch_many(
    [{"url": url, "max_retries": 2} for url in urls],
    request_delay=200,   # ms between request starts
    concurrency=3,       # at most 3 in flight
)
```

Results keep the input order. Check each response individually. For crawling with link discovery use a spider instead.

## User agents and proxies

`user_agent`, `proxy_url` and `proxy` accept a string or a **zero-argument callable**, evaluated on every request:

```python
from xcrap.utils import Randomizer, Rotator

proxies = Rotator(["http://user:pass@proxy-a:8080", "http://user:pass@proxy-b:8080"])

client = CurlCffiClient(
    impersonate="chrome120",
    user_agent=lambda: Randomizer.user_agent("chrome"),
    proxy_url=lambda: next(proxies),   # next() returns the current item, then advances
)
```

- `CurlCffiClient`, `PlaywrightClient`, `SeleniumClient`, `SeleniumBaseClient` use `proxy_url` (or `proxy`) as a real proxy server.
- `HttpxClient` treats `proxy_url` as a **URL prefix** (`f"{proxy_url}{url}"`, CORS/forwarding-proxy style) and ignores `proxy`. For a real proxy server with plain HTTP, use `CurlCffiClient`.
- SeleniumBase strips the scheme from proxies for you (`user:pass@host:port`).

## Browser clients

```python
client = PlaywrightClient(browser_type="chromium", headless=True, timeout=30_000, viewport={"width": 1280, "height": 800})

response = await client.fetch(
    url="https://example.com/js-page",
    actions=[
        {"type": "before_request", "func": lambda page: page.set_extra_http_headers({"X-Test": "1"})},
        lambda page: page.wait_for_selector("div.item", timeout=20_000),  # bare callable = after navigation
        {"type": "after_request", "func": lambda page: page.click("button.more")},
    ],
)
```

- The body is the rendered DOM after the actions.
- Playwright actions may be sync or async and receive the `Page`. Selenium/SeleniumBase actions are sync and receive the driver.
- **Each `fetch()` launches and closes a browser.** Requests are isolated but slow: keep `concurrency` low and use browsers only for the pages that need them.
- Wait for the element you need (`wait_for_selector`) instead of sleeping.
- `SeleniumBaseClient(uc=True, reconnect_time=3.0, headless=True, driver_options={...})`: raise `reconnect_time` for slow challenges. Its GUI helpers (`driver.uc_gui_click_captcha()`) need `headless=False`.
- Spiders do not forward `actions`: subclass the client and set them as defaults:

```python
class WaitForItems(PlaywrightClient):
    async def fetch(self, *args, **kwargs):
        kwargs.setdefault("actions", [lambda page: page.wait_for_selector("div.item")])
        return await super().fetch(*args, **kwargs)
```

## Decrypting responses

```python
from xcrap.core import decrypt_client, inject_decryptor
from xcrap.utils.decryption import DecryptConfig, DecryptKeyConfig

config = DecryptConfig(
    algorithm="aes-256-cbc", input_encoding="base64", output_encoding="utf-8",
    key=DecryptKeyConfig(value="0123456789abcdef0123456789abcdef"),
    iv=DecryptKeyConfig(value="abcdef9876543210"),
)
client = inject_decryptor(HttpxClient(), config)   # or decorate a class with @decrypt_client(config)
```

Successful responses arrive decrypted (header `x-xcrap-decrypted: true`). If decryption fails, the original response is returned.

## Custom clients

Subclass `HttpClientBase` and return `HttpResponse` objects; use `self._current_user_agent`, `self._current_proxy_url` and `self._current_proxy` (callables already resolved). Subclassing an existing client to add defaults is equally valid.

```python
from xcrap.core import HttpClientBase, HttpResponse


class MyClient(HttpClientBase):
    async def fetch(self, url, method="GET", retries=0, max_retries=0, retry_delay=0, headers=None):
        body = await my_transport(url, headers)
        return HttpResponse(status=200, status_text="OK", body=body, headers={})

    async def fetch_many(self, requests, request_delay, concurrency): ...
```

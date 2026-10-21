# Clients

A **client** fetches a URL and gives you an [`HttpResponse`](#httpresponse). All clients derive from `HttpClientBase` and share the same interface, so they are interchangeable in your own code and in [spiders](spiders.md).

| Client | Engine | Use it when | Extra |
| --- | --- | --- | --- |
| `HttpxClient` | `httpx` | Plain HTTP/JSON/HTML — the default and the fastest | — |
| `CurlCffiClient` | `curl-cffi` | The site blocks Python's TLS fingerprint (Cloudflare and friends) | `curl` |
| `PlaywrightClient` | Playwright | Content is rendered by JavaScript, or you need to click/scroll/type | `playwright` |
| `SeleniumClient` | Selenium WebDriver | You already depend on WebDriver | `selenium` |
| `SeleniumBaseClient` | [SeleniumBase](https://seleniumbase.io) (UC mode) | The site actively detects automation: Cloudflare Turnstile, CAPTCHAs, fingerprinting | `seleniumbase` |

```python
from xcrap.clients import CurlCffiClient, HttpxClient, PlaywrightClient, SeleniumBaseClient, SeleniumClient
```

## Fetching

```python
client = HttpxClient()
response = await client.fetch(
    url="https://quotes.toscrape.com",
    method="GET",
    max_retries=3,        # extra attempts after the first
    retry_delay=500,      # ms between attempts
    headers={"Accept-Language": "en"},
)
```

`fetch()` parameters:

| Parameter | Meaning |
| --- | --- |
| `url` | Target URL |
| `method` | HTTP method (ignored by the browser clients, which always navigate) |
| `max_retries` | How many times to retry after a failure |
| `retry_delay` | Milliseconds to wait between attempts |
| `headers` | Extra request headers, merged over the client's `User-Agent` |

Browser clients additionally accept `actions=` (see [Browser clients](#browser-clients)); `PlaywrightClient` also accepts `wait_until=`.

### Failures do not raise

A client never raises for network or HTTP errors. It returns a response describing the failure, so a long crawl is not killed by one bad URL:

```python
response = await client.fetch(url="https://example.com/missing", max_retries=2)

if not response.is_success():
    print(response.status, response.status_text)   # 404 NOT FOUND
    print(response.attempts)                        # 3
    print(response.failed_attempts)                 # [{"timestamp": ..., "error": "..."}, ...]
```

What counts as a failure depends on the client:

| Client | Retries on |
| --- | --- |
| `HttpxClient` | Exceptions **and** non-2xx statuses. After the last attempt you get the real status/body of the failing response (or status `500` with the error message for exceptions) |
| `CurlCffiClient`, `PlaywrightClient`, `SeleniumClient`, `SeleniumBaseClient` | Exceptions only (timeouts, connection errors, driver errors). A 404 page is returned as-is with its status; after the last attempt you get status `500` with an empty body |

`HttpxClient` follows redirects.

## HttpResponse

| Member | Description |
| --- | --- |
| `status`, `status_text` | Status code and reason |
| `body` / `text` | Response body as `str` |
| `json` | `json.loads(body)` (property) |
| `headers` | `dict` with **lower-cased** names |
| `get_header(name)` | Case-insensitive header lookup |
| `is_success()` | `200 <= status < 300` |
| `attempts`, `failed_attempts` | How many tries were made and why earlier ones failed |
| `as_html_parser()` | → [`HtmlParser`](extraction.md#html) |
| `as_json_parser()` | → [`JsonParser`](extraction.md#json) |
| `as_markdown_parser()` | → [`MarkdownParser`](extraction.md#markdown) |
| `as_parser(MyParser)` | Any `SourceParser` subclass |

## Many requests at once

`fetch_many()` runs a batch with bounded concurrency and an optional delay between request starts. Results come back in the **same order** as the input.

```python
responses = await client.fetch_many(
    [{"url": f"https://books.toscrape.com/catalogue/page-{n}.html", "max_retries": 2} for n in range(1, 11)],
    request_delay=100,   # ms between request starts
    concurrency=3,       # at most 3 in flight
)
```

Each request is a dict with the same keys as `fetch()`. For crawling with link discovery, prefer a [spider](spiders.md); for known URL lists (see [`StaticPaginator`](utilities.md#staticpaginator)) `fetch_many()` is ideal.

## User agents and proxies

Every client accepts `user_agent`, `proxy_url` and `proxy`. Each can be a **string or a zero-argument callable**; callables are evaluated on every request, which makes rotation trivial with [`Rotator`](utilities.md#rotator) and [`Randomizer`](utilities.md#randomizer):

```python
from xcrap.utils import Randomizer, Rotator

proxies = Rotator(["http://proxy-a:8080", "http://proxy-b:8080"])

client = CurlCffiClient(
    user_agent=lambda: Randomizer.user_agent("chrome"),
    proxy_url=lambda: next(proxies),
)
```

The default user agent is a recent desktop Chrome string (`xcrap.utils.DEFAULT_USER_AGENT`).

How proxies are applied:

- `CurlCffiClient`, `PlaywrightClient`, `SeleniumClient`, `SeleniumBaseClient` use `proxy_url` (or `proxy` if it is unset) as a regular proxy server.
- `HttpxClient` treats `proxy_url` as a **URL prefix** (the "forwarding proxy" style used by web proxies and Node Xcrap: the request goes to `f"{proxy_url}{url}"`). Its `proxy` argument is currently not applied.

## CurlCffiClient

Reproduces a real browser's TLS and HTTP/2 handshake, which is what anti-bot systems fingerprint first.

```python
client = CurlCffiClient(impersonate="chrome120", timeout=30.0)
```

`impersonate` accepts any profile curl-cffi supports (`chrome120`, `safari17_0`, `firefox…`). See [`examples/11_client_curl_cffi.py`](../examples/11_client_curl_cffi.py), which prints the JA3 hash each client presents to a TLS-echo service.

## Browser clients

`PlaywrightClient` and `SeleniumClient` load the page in a real browser and return the **rendered DOM** (`page.content()` / `driver.page_source`) as the body.

```python
client = PlaywrightClient(browser_type="chromium", headless=True, timeout=30_000, viewport={"width": 1280, "height": 800})
client = SeleniumClient(browser_type="chrome", headless=True, timeout=30.0)   # chrome | firefox | edge
```

> Each `fetch()` launches and closes a browser. That keeps requests isolated but is slow — use browser clients only for the pages that need them, and keep `concurrency` low.

### Actions

`actions=` runs code against the live page/driver. Plain callables run **after** navigation; dicts select the moment:

```python
response = await PlaywrightClient().fetch(
    url="https://quotes.toscrape.com/js-delayed/",
    actions=[
        {"type": "before_request", "func": lambda page: page.set_extra_http_headers({"X-Test": "1"})},
        lambda page: page.wait_for_selector("div.quote", timeout=20_000),        # after navigation
        {"type": "after_request", "func": lambda page: page.click("li.next a")},  # same as a bare callable
    ],
)
```

With Playwright, actions may be sync or `async` (coroutines are awaited) and receive the Playwright `Page`. With Selenium they are synchronous and receive the WebDriver (the call runs in a worker thread via `asyncio.to_thread`). Note that Selenium cannot see HTTP status codes, so its responses always report `200`.

Complete example: [`examples/12_client_playwright.py`](../examples/12_client_playwright.py).

## SeleniumBaseClient

[SeleniumBase](https://seleniumbase.io) wraps Selenium with a **UC (undetected-chromedriver) mode**: a patched Chrome that hides the usual automation fingerprints (`navigator.webdriver`, driver variables…) and can pass challenges such as Cloudflare Turnstile. Choose it when `PlaywrightClient`/`SeleniumClient` get blocked.

```python
client = SeleniumBaseClient(
    browser_type="chrome",     # SeleniumBase browser name
    headless=True,
    uc=True,                   # undetected mode (default). False -> a plain driver.get()
    reconnect_time=3.0,        # seconds the driver stays disconnected while challenges run
    timeout=30.0,              # page load timeout
    driver_options={"incognito": True},   # any other seleniumbase.Driver(...) argument
)
response = await client.fetch(url="https://example.com")
```

How it behaves:

- In UC mode the page is opened with `driver.uc_open_with_reconnect(url, reconnect_time)`: the driver disconnects while the site's bot checks run, then reconnects. Raise `reconnect_time` for slow challenges.
- `user_agent`, `proxy_url`/`proxy` are applied like in the other clients. SeleniumBase wants proxies as `host:port` or `user:pass@host:port`, so a scheme (`http://`) is stripped for you.
- Like `SeleniumClient`, it reports status `200` for any rendered page (WebDriver cannot read HTTP status or response headers), and `headers=` passed to `fetch()` are not applied. Failures (driver crash, timeout) are retried according to `max_retries`, then returned as status `500`.
- Each `fetch()` starts and quits its own browser, run in a worker thread; keep `concurrency` low.

### Actions

Same `actions=` contract as the other browser clients (a bare callable runs after navigation; dicts with `"type": "before_request" | "after_request"` choose the moment), but they receive the **SeleniumBase driver**, which adds anti-bot helpers on top of the WebDriver API:

```python
response = await client.fetch(
    url="https://protected.example.com",
    actions=[
        lambda driver: driver.uc_gui_click_captcha(),                 # click a CAPTCHA / Turnstile checkbox
        lambda driver: driver.execute_script("window.scrollTo(0, document.body.scrollHeight)"),
    ],
)
```

`uc_gui_click_captcha()` and friends use GUI automation, so they need a real (non-headless) display: pass `headless=False` when you rely on them.

Runnable: [`examples/15_client_seleniumbase.py`](../examples/15_client_seleniumbase.py). Tip: SeleniumBase downloads a matching driver the first time it runs, so the first fetch is slower. To use actions from a spider, see [Spiders → Using other clients](spiders.md#using-other-clients).

## Decrypting responses

Some APIs return AES-encrypted bodies. Wrap a client class (or instance) and every successful response is decrypted before you see it; the response gets an `x-xcrap-decrypted: true` header.

```python
from xcrap.core import decrypt_client, decrypt_response, inject_decryptor
from xcrap.utils.decryption import DecryptConfig, DecryptKeyConfig

config = DecryptConfig(
    algorithm="aes-256-cbc",        # aes-*-cbc or aes-*-ecb, PKCS7 padding
    input_encoding="hex",            # how the ciphertext is encoded: hex | base64
    output_encoding="utf-8",
    key=DecryptKeyConfig(value="0123456789abcdef0123456789abcdef"),   # encoding defaults to utf-8
    iv=DecryptKeyConfig(value="abcdef9876543210"),
)

@decrypt_client(config)           # decorate a client class…
class SecureClient(HttpxClient): ...

client = inject_decryptor(HttpxClient(), config)   # …or patch an instance
plain = decrypt_response(response, config)         # …or decrypt one response you already have
```

If decryption fails, the original response is returned untouched. Runnable offline demo: [`examples/14_decryption.py`](../examples/14_decryption.py).

## Writing your own client

Subclass `HttpClientBase`, implement `fetch()` and `fetch_many()`, and return `HttpResponse` objects. The base class gives you `_current_user_agent`, `_current_proxy_url`, `_current_proxy` (callables already resolved) and helpers for concurrency (`_execute_request`, `_should_throttle`, `_handle_concurrency`).

```python
from xcrap.core import HttpClientBase, HttpResponse


class MyClient(HttpClientBase):
    async def fetch(self, url, method="GET", retries=0, max_retries=0, retry_delay=0, headers=None):
        body = await my_transport(url, headers)
        return HttpResponse(status=200, status_text="OK", body=body, headers={})

    async def fetch_many(self, requests, request_delay, concurrency):
        ...
```

A custom client is a drop-in for every parser and spider; subclassing an existing one to add defaults (for example to always pass `actions`) is just as valid.

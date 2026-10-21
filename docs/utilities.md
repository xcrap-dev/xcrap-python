# Utilities

Small, independent helpers: `from xcrap.utils import Rotator, Randomizer, StaticPaginator` (they are also re-exported from `xcrap.core`).

## Rotator

Cycles through a list in order — proxies, user agents, API tokens.

```python
from xcrap.utils import Rotator

proxies = Rotator(["http://p1:8080", "http://p2:8080", "http://p3:8080"])

proxies.current      # 'http://p1:8080'   (does not advance)
proxies.rotate()     # 'http://p2:8080'   (advances, returns the new current; `next()` is an alias)
proxies.reset()      # back to the first
len(proxies)         # 3
next(proxies)        # returns the current item, THEN advances; never raises StopIteration
```

Wrap `next(...)` in a `lambda` and it becomes the zero-argument callable that clients accept for `user_agent` / `proxy_url`:

```python
client = CurlCffiClient(proxy_url=lambda: next(proxies))     # a different proxy on every request
```

An empty list raises `EmptyListError`.

## Randomizer

Picks a random element, and generates realistic user agents.

```python
from xcrap.utils import MODERN_USER_AGENTS, Randomizer

Randomizer(["a", "b", "c"]).random()          # one at random
Randomizer.user_agent()                        # any modern desktop UA
Randomizer.user_agent("firefox")               # chrome | firefox | safari | edge

client = HttpxClient(user_agent=lambda: Randomizer.user_agent("chrome"))
```

`MODERN_USER_AGENTS` is the underlying list of current Chrome/Firefox/Safari/Edge strings.

## StaticPaginator

Handles sites whose pages are addressed by a number in the URL (`/page/2`, `?p=3`, `page-4.html`). The template contains a `{page}` placeholder; a template without it raises `InvalidUrlError`.

```python
from xcrap.utils import StaticPaginator

paginator = StaticPaginator(initial_page=1, last_page=50, template_url="https://books.toscrape.com/catalogue/page-{page}.html")

paginator.current            # .../page-1.html
paginator.next()             # .../page-2.html (advances)
paginator.previous()         # .../page-1.html
paginator.set(10)            # jump to page 10
paginator.dump()             # URLs from the current page to the last one
paginator.dump(limit=5)      # at most 5 URLs: pages 10..14
```

Moving outside `[min_page, last_page]` raises `PageOutOfRangeError`. `min_page` defaults to `initial_page`.

### Discovering the range automatically

Most sites print "Page 1 of 50". `create_with_tracking()` fetches the first page, reads the numbers with *trackers*, and returns the paginator together with the response it already downloaded (so you do not fetch page 1 twice):

```python
tracked = await StaticPaginator.create_with_tracking(
    client=HttpxClient(),
    request="https://books.toscrape.com/catalogue/page-1.html",     # a URL, or a dict of fetch() arguments
    template_url="https://books.toscrape.com/catalogue/page-{page}.html",
    trackers={
        "current_page": {"query": css("li.current")},
        "last_page": {
            "query": css("li.current"),
            "transformer": lambda raw: int(re.findall(r"\d+", raw)[-1]),   # "Page 1 of 50" -> 50
        },
    },
)
tracked["paginator"], tracked["response"], tracked["parser"]
```

A tracker has a `query`, an optional `extractor(selector)` (default: the element's HTML) and an optional `transformer(raw)` that must return an integer. Without a transformer the **first number** found in the value is used. Failures raise `PageParsingFailureError` (nothing matched) or `InvalidPageValueError` (not a number).

Feed the result to `fetch_many()` or to a spider: [`examples/10_fetch_many_and_pagination.py`](../examples/10_fetch_many_and_pagination.py).

## Errors

Everything Xcrap raises derives from `XcrapError`, so one `except XcrapError` catches the framework's own errors.

| Error | Raised when |
| --- | --- |
| `XcrapError` | Base class |
| `DependencyMissingError` | An optional extra is not installed (also an `ImportError`); the message contains the `pip install xcrap[...]` to run |
| `EmptyListError` | `Rotator`/`Randomizer` created with no values |
| `StaticPaginatorError` | Base of the paginator errors |
| `InvalidUrlError` | Template URL lacks `{page}` |
| `PageOutOfRangeError` | Page outside the allowed range (has `.page`, `.min_page`, `.last_page`) |
| `TrackingError` | Base of automatic-tracking errors |
| `PageParsingFailureError` | A tracker found nothing |
| `InvalidPageValueError` | A tracked value is not an integer |
| `InvalidMarkdownBody` | A Markdown body cannot be parsed |
| `DropItem` | Raised **by you** inside a [pipeline](spiders.md#item-pipelines) to discard an item |

```python
from xcrap.core import DependencyMissingError, XcrapError
```

Remember that [clients do not raise on HTTP errors](clients.md#failures-do-not-raise); these exceptions are for misuse and missing dependencies.

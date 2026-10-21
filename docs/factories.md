# Factories

Factories build framework objects from **plain data** — dictionaries you can load from JSON, YAML, environment variables or a database. They let you change *what* a bot scrapes without changing code.

All factories are *allow-list based*: you pass the classes and functions the configuration is allowed to name. Anything else raises `ValueError`, so a config file can never instantiate arbitrary code.

```python
from xcrap.factory import create_client, create_extraction_model, create_extractor
```

## create_client

```python
client = create_client(
    client_type="httpx",
    allowed_clients={"httpx": HttpxClient, "curl": CurlCffiClient},
    options={"user_agent": "my-bot/1.0", "proxy_url": "http://proxy:8080"},
)
```

`options` become the constructor's keyword arguments. An unknown `client_type` raises `ValueError("'x' is not a valid type of client!")`.

## create_extractor

Extractors are the functions you pass to a field's `extractor=`. A factory turns a **string** into one, optionally with arguments separated by `:`.

```python
allowed_extractors = {
    "attr": lambda name: (lambda el: el.attrib.get(name)),       # a *generator*: takes the arguments, returns the extractor
    "upper": lambda: (lambda el: el.get().upper()),
}

get_src = create_extractor("attr:src", allowed_extractors)        # calls generator("src")
shout = create_extractor("upper", allowed_extractors)
```

The separator defaults to `":"` and can be changed (`argument_separator="|"`).

## create_extraction_model

Builds a model recursively from a dictionary:

```python
config = {
    "type": "html",                                   # which allowed model class to use
    "model": {                                        # field name -> field definition
        "title": {"query": {"type": "css", "value": "h1::text"}},
        "image": {"query": {"type": "css", "value": "img"}, "extractor": "attr:src"},
        "items": {
            "query": {"type": "css", "value": "li"},
            "multiple": True,
            "limit": 10,
            "default": [],
            "nested": {                               # a nested model, same structure
                "type": "html",
                "model": {"name": {"query": {"type": "css", "value": "span::text"}}},
            },
        },
    },
}

model = create_extraction_model(
    config,
    allowed_models={"html": HtmlExtractionModel, "json": JsonExtractionModel},
    allowed_extractors=allowed_extractors,            # required; pass {} if you use none
)

data = model.extract(html)
```

Field definition keys: `query` (`{"type": "css" | "xpath" | "jmes_path", "value": "..."}`), `multiple`, `limit`, `default`, `extractor` (a string resolved by `create_extractor`; HTML models only) and `nested`.

The `type` selects the class: an `HtmlExtractionModel` subclass produces `HtmlBaseField`/`HtmlNestedField`s, a `JsonExtractionModel` subclass produces the JSON equivalents, so the same configuration style covers both formats (a `MarkdownExtractionModel` works like HTML).

The result is an ordinary model **instance**: call `model.extract(content)` (HTML string, `Selector` or, for JSON models, a string/`dict`/`list`), or use it as the `model=` of a nested field. Parser helpers such as `parser.extract_model()` expect a model *class*, so with factory-built models call `model.extract()` yourself.

## Putting it together: a bot defined entirely by data

```python
import json

bot = json.load(open("bot.json"))     # {"client": {...}, "url": "...", "model": {...}}

client = create_client(bot["client"]["type"], ALLOWED_CLIENTS, bot["client"].get("options", {}))
model = create_extraction_model(bot["model"], ALLOWED_MODELS, ALLOWED_EXTRACTORS)

response = await client.fetch(url=bot["url"])
data = model.extract(response.text)
```

Adding a site is then a new JSON file, not a deployment. For a runnable version of this idea see [`examples/13_rotation_and_factories.py`](../examples/13_rotation_and_factories.py).

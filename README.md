# Xcrap for Python

Xcrap é um framework originalmente feito para Node.js, mas, digamos que eu também sou um desenvolvedor Python e, estava um pouco entediado; por isso, resolvi fazer uma versão para Python.

Ainda está em fase experimental, mas já conta com funcionalidades poderosas portadas da versão original em TypeScript, garantindo paridade entre os ecossistemas.

## 🚀 Como funciona

A ideia é ser declarativo e fácil. Veja um exemplo de como você já pode usar o `xcrap` para extrair dados estruturados:

```python
from xcrap.extractor import HtmlExtractionModel, HtmlBaseField, HtmlNestedField, css
from xcrap.clients import HttpxClient
import asyncio

# 1. Defina seus modelos de forma declarativa
class AuthorModel(HtmlExtractionModel):
    name = HtmlBaseField(query=css("small.author::text"))
    link = HtmlBaseField(query=css("a::attr(href)"))

class QuoteModel(HtmlExtractionModel):
    text = HtmlBaseField(query=css("span.text::text"))
    # Modelos aninhados sem esforço!
    author = HtmlNestedField(model=AuthorModel) 
    tags = HtmlBaseField(query=css("div.tags a.tag::text"), multiple=True)

class QuotesPageModel(HtmlExtractionModel):
    quotes = HtmlNestedField(query=css("div.quote"), model=QuoteModel, multiple=True)

async def main():
    client = HttpxClient()
    
    # 2. Busque a página
    response = await client.fetch(url="http://quotes.toscrape.com")

    # 3. Transforme em um parser e extraia os dados
    parser = response.as_html_parser()
    data = parser.extract_model(QuotesPageModel)

    for quote in data["quotes"][:3]:
        print(f"Quote: {quote['text']}")
        print(f"Author: {quote['author']['name']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## ✨ Funcionalidades Principais

### 🔒 Descriptografia Automática
Suporte integrado para descriptografar respostas HTTP (AES-CBC/ECB).

```python
from xcrap.core import decrypt_client
from xcrap.utils.decryption import DecryptConfig, DecryptKeyConfig

config = DecryptConfig(
    algorithm="aes-256-cbc",
    key=DecryptKeyConfig(value="sua-chave-aqui"),
    iv=DecryptKeyConfig(value="seu-iv-aqui")
)

@decrypt_client(config)
class MySecureClient(HttpxClient):
    pass

# Todas as respostas deste cliente agora virão descriptografadas!
```

### 🏭 Sistema de Factories
O sistema de Factory permite a criação dinâmica de componentes a partir de arquivos de configuração (JSON/Dict), facilitando a manutenção de bots sem alteração de código.

#### 1. Model Factory
Constrói modelos complexos de forma recursiva:

```python
from xcrap.factory import create_extraction_model
from xcrap.extractor import HtmlExtractionModel

config = {
    "type": "html",
    "model": {
        "title": {"query": {"type": "css", "value": "h1::text"}},
        "items": {
            "query": {"type": "css", "value": "li"},
            "multiple": true,
            "nested": {
                "type": "html",
                "model": {"name": {"query": {"type": "css", "value": "span::text"}}}
            }
        }
    }
}

model = create_extraction_model(config, allowed_models={"html": HtmlExtractionModel})
```

#### 2. Client Factory
Instancia clientes com configurações específicas:

```python
from xcrap.factory import create_client
from xcrap.clients import HttpxClient

client = create_client(
    client_type="httpx",
    allowed_clients={"httpx": HttpxClient},
    options={"user_agent": "CustomAgent", "proxy_url": "http://..."}
)
```

#### 3. Extractor Factory
Cria extratores a partir de strings, suportando argumentos:

```python
from xcrap.factory import create_extractor

# 'attr:src' chamará o gerador 'attr' com o argumento 'src'
get_src = create_extractor("attr:src", allowed_extractors={"attr": lambda a: lambda el: el.attrib.get(a)})
```

### 🛠️ Extratores Customizados
Você pode passar funções customizadas para processar campos individualmente:

```python
class MyModel(HtmlExtractionModel):
    # 'extractor' permite transformar o dado logo após a captura
    price = HtmlBaseField(
        query=css(".price::text"), 
        extractor=lambda text: float(text.replace("$", ""))
    )
```

### 📊 Extração de JSON (JMESPath)
Também suportamos extração de JSON usando JMESPath:

```python
from xcrap.extractor import JsonExtractionModel, JsonBaseField, jmes_path, JsonParser

class ProjectModel(JsonExtractionModel):
    name = JsonBaseField(query=jmes_path("title"))
    tags = JsonBaseField(query=jmes_path("tags"), multiple=True)

content = '{"title": "Xcrap", "tags": ["python", "scraping"]}'
parser = JsonParser(content)
data = parser.extract_model(ProjectModel) # {'name': 'Xcrap', 'tags': ['python', 'scraping']}
```

### 🕷️ Spiders

Inspirados no Scrapy, mas adaptados ao Xcrap: tudo é `asyncio` nativo, o client (`HttpxClient`, `CurlCffiClient`, `PlaywrightClient`) já cuida de retry, proxy e user agent (por isso não há *downloader middlewares*) e a extração continua sendo feita pelos modelos declarativos.

```python
from xcrap.extractor import css
from xcrap.spiders import DropItem, ItemPipeline, JsonLinesPipeline, Spider


class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["http://quotes.toscrape.com"]
    concurrency = 4
    request_delay = 200  # ms entre requisições
    max_retries = 2

    async def parse(self, response):
        parser = response.as_html_parser()

        for quote in parser.extract_models(QuoteModel, css("div.quote")):
            yield quote  # dict ou modelo pydantic = item

        for href in parser.extract_values(css("li.next a::attr(href)")):
            yield response.follow(href)  # Request = continua o crawl
            # response.follow(href, callback="parse_other") para outro callback


class NoEmptyText(ItemPipeline):
    async def process_item(self, item, spider):
        if not item["text"]:
            raise DropItem("sem texto")
        return item


stats = QuotesSpider(pipelines=[NoEmptyText(), JsonLinesPipeline("quotes.jsonl")]).run()
```

- `await spider.crawl()` / `spider.run()` executam e devolvem `SpiderStats`; `await spider.collect()` devolve os itens e `async for item in spider.stream()` os entrega conforme chegam.
- `Request` aceita `callback`/`errback` (função ou nome do método), `meta`, `priority`, `dont_filter`, `max_retries` e `retry_delay`.
- Configurações da classe (ou kwargs do construtor): `concurrency`, `request_delay`, `max_retries`, `retry_delay`, `headers`, `max_requests`, `max_depth`, `dedupe`.
- Respostas não-2xx vão para o `errback` do request ou para `Spider.on_error`; exceções em callbacks são logadas e contadas, sem parar o crawl.
- `ModelSpider` dispensa o `parse`: defina `model`, e opcionalmente `items_query` (um item por elemento) e `follow_query` (links a seguir).

```python
class QuotesSpider(ModelSpider):
    start_urls = ["http://quotes.toscrape.com"]
    model = QuoteModel
    items_query = css("div.quote")
    follow_query = css("li.next a::attr(href)")
```

Para paginação estática, use `start_urls = paginator.dump()` com o `StaticPaginator`.

## 🛠️ Desenvolvimento

Para rodar os testes e verificar a cobertura:

```bash
poetry run pytest --cov=xcrap --cov-report=term-missing
```

Atualmente o projeto conta com **100% de cobertura de código**, garantindo a confiabilidade de todas as funcionalidades.

---
Feito com ❤️ por Marcuth <contact@marcuth.dev>

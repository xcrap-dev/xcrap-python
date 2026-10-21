import pytest

from xcrap.extractor import HtmlBaseField, HtmlExtractionModel, HtmlNestedField, HtmlParser
from xcrap.extractor.query_builders import css, xpath

parser = HtmlParser("""
<html>
<head>
    <title>Document</title>
</head>
<body>
    <h1 class="title">This is a heading</h1>
    <p id="description">Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras egestas justo nunc, vitae aliquam augue rhoncus congue. Nulla vel urna turpis. Mauris sagittis ullamcorper lacinia. Ut ut elit at mauris auctor vulputate sit amet nec tortor. Aliquam rutrum sollicitudin massa, id semper velit vulputate sed. Maecenas in porttitor justo, non laoreet libero. In non lacus et velit pulvinar pretium eget id metus. Donec eget vehicula massa, et mattis sem. Sed magna eros, dapibus eget scelerisque vel, tincidunt at ante. Nunc tempus risus felis, non porttitor nibh laoreet et. Aliquam vitae lorem quis orci tincidunt ultricies. Fusce euismod tristique augue, eget malesuada justo mollis eget. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas.</p>
    <ul class="list">
        <li class="item">Item 1</li>
        <li class="item">Item 2</li>
        <li class="item">Item 3</li>
        <li class="item">Item 4</li>
    </ul>
    <section id="profile">
        <span id="display-name">Marcuth Dev</span>
        <span id="username">marcuth</span>
        <div id="skills">
            <ul id="web-development">
                <li>NestJS</li>
                <li>PostgreSQL</li>
                <li>Prisma</li>
                <li>Supabase</li>
            </ul>
            <ul id="web-automation">
                <li>Puppeteer</li>
                <li>Playwright</li>
                <li>Selenium</li>
            </ul>
        </div>
    </section>
</body>
</html>
""")


def test_html_extraction_model_should_exists() -> None:
    assert HtmlExtractionModel


def test_html_base_field_should_exists() -> None:
    assert HtmlBaseField


def test_html_nested_field_should_exists() -> None:
    assert HtmlNestedField


def test_html_extraction_model_should_extract_single_base_fields() -> None:
    expected = {
        "title": "This is a heading",
        "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras egestas justo nunc, vitae aliquam augue rhoncus congue. Nulla vel urna turpis. Mauris sagittis ullamcorper lacinia. Ut ut elit at mauris auctor vulputate sit amet nec tortor. Aliquam rutrum sollicitudin massa, id semper velit vulputate sed. Maecenas in porttitor justo, non laoreet libero. In non lacus et velit pulvinar pretium eget id metus. Donec eget vehicula massa, et mattis sem. Sed magna eros, dapibus eget scelerisque vel, tincidunt at ante. Nunc tempus risus felis, non porttitor nibh laoreet et. Aliquam vitae lorem quis orci tincidunt ultricies. Fusce euismod tristique augue, eget malesuada justo mollis eget. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas.",
    }

    class MyExtractionModel(HtmlExtractionModel):
        title = HtmlBaseField(query=css("h1.title::text"))
        description = HtmlBaseField(query=css("p#description::text"))

    data = parser.extract_model(MyExtractionModel)

    assert expected == data


def test_html_extraction_model_should_return_default_value_when_element_dont_exists() -> None:
    expected = {"xpto": "DEFAULT_VALUE"}

    class MyExtractionModel(HtmlExtractionModel):
        xpto = HtmlBaseField(query=css(".xpto"), default="DEFAULT_VALUE")

    data = parser.extract_model(MyExtractionModel)

    assert expected == data


def test_html_extraction_model_should_extract_multiple_base_fields() -> None:
    expected = {"items": ["Item 1", "Item 2", "Item 3", "Item 4"]}

    class MyExtractionModel(HtmlExtractionModel):
        items = HtmlBaseField(query=css("ul.list li.item::text"), multiple=True)

    data = parser.extract_model(MyExtractionModel)

    assert expected == data


def test_html_extraction_model_should_extract_multiple_base_fields_with_limit() -> None:
    expected = {"items": ["Item 1", "Item 2"]}

    class MyExtractionModel(HtmlExtractionModel):
        items = HtmlBaseField(query=css("ul.list li.item::text"), multiple=True, limit=2)

    data = parser.extract_model(MyExtractionModel)

    assert expected == data


def test_html_extraction_model_extract_nested_model_without_query() -> None:
    expected = {"headings": {"title": "This is a heading"}}

    class MyNestedExtractionModel(HtmlExtractionModel):
        title = HtmlBaseField(query=css("h1.title::text"))

    class MyExtractionModel(HtmlExtractionModel):
        headings = HtmlNestedField(model=MyNestedExtractionModel)

    data = parser.extract_model(MyExtractionModel)

    assert expected == data


def test_html_extraction_model_extract_nested_model_with_query() -> None:
    expected = {"profile": {"name": "Marcuth Dev", "username": "marcuth"}}

    class MyNestedExtractionModel(HtmlExtractionModel):
        name = HtmlBaseField(query=css("span#display-name::text"))
        username = HtmlBaseField(query=css("span#username::text"))

    class MyExtractionModel(HtmlExtractionModel):
        profile = HtmlNestedField(query=css("section#profile"), model=MyNestedExtractionModel)

    data = parser.extract_model(MyExtractionModel)

    assert expected == data


def test_html_extraction_model_should_return_default_when_not_found_nested_element() -> None:
    expected = {"user": {"name": "Marcuth"}}

    class MyNestedExtractionModel(HtmlExtractionModel):
        name = HtmlBaseField(query=css("span#display-name::text"))

    class MyExtractionModel(HtmlExtractionModel):
        user = HtmlNestedField(query=css(".a-false-query"), model=MyNestedExtractionModel, default=expected["user"])

    data = parser.extract_model(MyExtractionModel)

    assert expected == data


def test_html_extraction_model_should_raise_exception_when_not_defined_query_on_multiple_nested_model() -> None:
    class MyNestedExtractionModel(HtmlExtractionModel):
        name = HtmlBaseField(query=css("xpto"))

    class MyExtractionModel(HtmlExtractionModel):
        user = HtmlNestedField(
            model=MyNestedExtractionModel,
            multiple=True,
        )

    with pytest.raises(Exception):
        parser.extract_model(MyExtractionModel)


def test_html_extraction_model_should_extract_multiple_nested_models_with_limit() -> None:
    expected = {
        "items": [
            {"name": "Item 1"},
            {"name": "Item 2"},
        ]
    }

    class MyItemModel(HtmlExtractionModel):
        name = HtmlBaseField(query=css("::text"))

    class MyExtractionModel(HtmlExtractionModel):
        items = HtmlNestedField(query=css("ul.list li.item"), model=MyItemModel, multiple=True, limit=2)

    data = parser.extract_model(MyExtractionModel)

    assert expected == data


def test_html_extraction_model_should_return_default_for_multiple_nested_models_if_none_found() -> None:
    expected = {"items": ["DEFAULT"]}

    class MyItemModel(HtmlExtractionModel):
        name = HtmlBaseField(query=css("::text"))

    class MyExtractionModel(HtmlExtractionModel):
        items = HtmlNestedField(query=css(".non-existent"), model=MyItemModel, multiple=True, default=["DEFAULT"])

    data = parser.extract_model(MyExtractionModel)

    assert expected == data


def test_html_extraction_model_should_use_xpath_queries() -> None:
    expected = {"title": "This is a heading"}

    class MyExtractionModel(HtmlExtractionModel):
        title = HtmlBaseField(query=xpath("//h1[@class='title']/text()"))

    data = parser.extract_model(MyExtractionModel)

    assert expected == data


def test_html_extraction_model_inheritance() -> None:
    class BaseExtractionModel(HtmlExtractionModel):
        title = HtmlBaseField(query=css("h1.title::text"))

    class ChildExtractionModel(BaseExtractionModel):
        description = HtmlBaseField(query=css("p#description::text"))

    expected = {
        "title": "This is a heading",
        "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras egestas justo nunc, vitae aliquam augue rhoncus congue. Nulla vel urna turpis. Mauris sagittis ullamcorper lacinia. Ut ut elit at mauris auctor vulputate sit amet nec tortor. Aliquam rutrum sollicitudin massa, id semper velit vulputate sed. Maecenas in porttitor justo, non laoreet libero. In non lacus et velit pulvinar pretium eget id metus. Donec eget vehicula massa, et mattis sem. Sed magna eros, dapibus eget scelerisque vel, tincidunt at ante. Nunc tempus risus felis, non porttitor nibh laoreet et. Aliquam vitae lorem quis orci tincidunt ultricies. Fusce euismod tristique augue, eget malesuada justo mollis eget. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas.",
    }

    data = parser.extract_model(ChildExtractionModel)

    assert expected == data


def test_extraction_model_abstract_call() -> None:
    from xcrap.extractor.extraction_model import ExtractionModel

    class ConcreteModel(ExtractionModel):
        def extract(self, content: str) -> any:
            return super().extract(content)

    model = ConcreteModel()

    assert model.extract("anything") is None


def test_html_extraction_model_multiple_no_results_no_default():
    class MyExtractionModel(HtmlExtractionModel):
        items = HtmlBaseField(query=css(".missing"), multiple=True)

    data = parser.extract_model(MyExtractionModel)
    assert data["items"] == []


def test_html_extraction_model_nested_with_model_type():
    class SubModel(HtmlExtractionModel):
        text = HtmlBaseField(query=css("h1::text"))

    class MyModel(HtmlExtractionModel):
        sub = HtmlNestedField(model=SubModel)

    data = parser.extract_model(MyModel)
    assert data["sub"]["text"] == "This is a heading"


def test_html_extraction_model_with_extractors():
    parser_with_link = HtmlParser('<a href="https://xcrap.com">Link</a>')

    class MyModel(HtmlExtractionModel):
        link = HtmlBaseField(query=css("a"), extractor=lambda el: el.attrib.get("href"))
        tags = HtmlBaseField(query=css("a"), multiple=True, extractor=lambda el: el.root.tag)

    data = parser_with_link.extract_model(MyModel)
    assert data["link"] == "https://xcrap.com"
    assert data["tags"] == ["a"]

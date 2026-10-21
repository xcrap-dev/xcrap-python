from xcrap.extractor import HtmlBaseField, HtmlExtractionModel, HtmlParser
from xcrap.extractor.query_builders import css, xpath


def test_html_parser_extract_value() -> None:
    html = '<h1 class="title">Hello World</h1>'
    parser = HtmlParser(html)

    assert parser.extract_value(css("h1.title::text")) == "Hello World"
    assert parser.extract_value(css("h2.title::text"), default="Default") == "Default"


def test_html_parser_extract_values() -> None:
    html = "<ul><li>1</li><li>2</li><li>3</li></ul>"
    parser = HtmlParser(html)

    assert parser.extract_values(css("li::text")) == ["1", "2", "3"]
    assert parser.extract_values(css("li::text"), limit=2) == ["1", "2"]


def test_html_parser_extract_model_with_query() -> None:
    html = '<div class="item"><h1>Title</h1></div>'
    parser = HtmlParser(html)

    class MyModel(HtmlExtractionModel):
        title = HtmlBaseField(query=css("h1::text"))

    data = parser.extract_model(MyModel, query=css("div.item"))
    assert data == {"title": "Title"}


def test_html_parser_extract_models() -> None:
    html = '<div class="item"><h1>Title 1</h1></div><div class="item"><h1>Title 2</h1></div>'
    parser = HtmlParser(html)

    class MyModel(HtmlExtractionModel):
        title = HtmlBaseField(query=css("h1::text"))

    data = parser.extract_models(MyModel, query=css("div.item"))
    assert data == [{"title": "Title 1"}, {"title": "Title 2"}]

    data = parser.extract_models(MyModel, query=css("div.item"), limit=1)
    assert data == [{"title": "Title 1"}]


def test_html_parser_xpath() -> None:
    html = '<h1 class="title">Hello World</h1>'
    parser = HtmlParser(html)

    assert parser.extract_value(xpath("//h1[@class='title']/text()")) == "Hello World"

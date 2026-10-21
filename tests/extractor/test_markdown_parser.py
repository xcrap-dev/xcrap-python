import textwrap

from xcrap.core.http_response import HttpResponse
from xcrap.extractor.html_extraction_model import HtmlBaseField
from xcrap.extractor.markdown_extraction_model import MarkdownExtractionModel
from xcrap.extractor.markdown_parser import MarkdownParser, render_markdown_to_html
from xcrap.extractor.query_builders import css


def test_render_markdown_to_html():
    md = "# Hello World\n\nThis is a [link](https://example.com)."
    html_output = render_markdown_to_html(md)
    assert "<h1" in html_output
    assert "Hello World</h1>" in html_output
    assert 'href="https://example.com"' in html_output


def test_markdown_parser():
    md = textwrap.dedent("""
    # Product Catalog

    - Item 1
    - Item 2
    - Item 3
    """).strip()

    parser = MarkdownParser(md)
    assert parser.markdown_source == md

    title = parser.extract_value(css("h1::text"))
    assert title == "Product Catalog"

    items = parser.extract_values(css("li::text"))
    assert items == ["Item 1", "Item 2", "Item 3"]


def test_markdown_extraction_model():
    class DocModel(MarkdownExtractionModel):
        title = HtmlBaseField(query=css("h1::text"))
        first_item = HtmlBaseField(query=css("ul li:first-child::text"))
        links = HtmlBaseField(query=css("a::attr(href)"), multiple=True)

    md = textwrap.dedent("""
    # Documentation

    * Section A
    * Section B

    Visit [Google](https://google.com) or [GitHub](https://github.com).
    """).strip()

    model = DocModel()
    data = model.extract(md)

    assert data["title"] == "Documentation"
    assert data["first_item"] == "Section A"
    assert data["links"] == ["https://google.com", "https://github.com"]


def test_http_response_as_markdown_and_json_parser():
    md_content = "# Test Document"
    resp = HttpResponse(status=200, status_text="OK", body=md_content, headers={})
    md_parser = resp.as_markdown_parser()
    assert isinstance(md_parser, MarkdownParser)
    assert md_parser.extract_value(css("h1::text")) == "Test Document"

    json_content = '{"greeting": "hello"}'
    resp_json = HttpResponse(status=200, status_text="OK", body=json_content, headers={})
    json_parser = resp_json.as_json_parser()
    from xcrap.extractor.query_builders import jmes_path
    assert json_parser.extract_value(jmes_path("greeting")) == "hello"


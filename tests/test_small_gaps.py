from unittest.mock import patch

from parsel import Selector

from xcrap.core.errors import InvalidMarkdownBody, InvalidPageValueError
from xcrap.extractor import HtmlBaseField, HtmlParser, MarkdownExtractionModel, css
from xcrap.ocr import image_text_extractor


def test_default_error_messages():
    assert "not valid numbers" in str(InvalidPageValueError())
    assert str(InvalidMarkdownBody()) == "Invalid Markdown body."


def test_html_parser_root_is_the_selector():
    parser = HtmlParser("<b>x</b>")

    assert parser.root is parser.selector


def test_markdown_model_accepts_an_existing_selector():
    class Model(MarkdownExtractionModel):
        title = HtmlBaseField(query=css("h1::text"))

    assert Model().extract(Selector(text="<h1>Hi</h1>")) == {"title": "Hi"}


def test_image_text_extractor_accepts_raw_values():
    with patch("xcrap.ocr.extract_image_text", return_value="text") as extract:
        assert image_text_extractor(lang="por")(b"bytes") == "text"

    extract.assert_called_once_with(b"bytes", lang="por", config="")


def test_playwright_action_normalizes_its_type():
    from xcrap.clients import PlaywrightAction

    action = PlaywrightAction("After_Request", print)

    assert action.action_type == "after_request"
    assert action.func is print

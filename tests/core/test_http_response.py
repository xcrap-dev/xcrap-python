from xcrap.core.http_response import HttpResponse
from xcrap.extractor.html_parser import HtmlParser
from xcrap.extractor.source_parser import SourceParser


def test_http_response_initialization() -> None:
    res = HttpResponse(status=200, status_text="OK", body='{"foo": "bar"}', headers={"content-type": "application/json"})

    assert res.status == 200
    assert res.status_text == "OK"
    assert res.body == '{"foo": "bar"}'
    assert res.headers == {"content-type": "application/json"}
    assert res.attempts is None
    assert res.failed_attempts is None


def test_http_response_is_success() -> None:
    assert HttpResponse(200, "OK", "", {}).is_success() is True
    assert HttpResponse(299, "OK", "", {}).is_success() is True
    assert HttpResponse(300, "Redir", "", {}).is_success() is False
    assert HttpResponse(404, "Not Found", "", {}).is_success() is False
    assert HttpResponse(500, "Error", "", {}).is_success() is False


def test_http_response_get_header() -> None:
    res = HttpResponse(200, "OK", "", {"Content-Type": "text/html", "X-Custom": "val"})
    assert res.get_header("Content-Type") == "text/html"
    assert res.get_header("content-type") == "text/html"
    assert res.get_header("X-Custom") == "val"
    assert res.get_header("Missing") is None


def test_http_response_text_property() -> None:
    res = HttpResponse(200, "OK", "Hello", {})
    assert res.text == "Hello"


def test_http_response_json_property() -> None:
    res = HttpResponse(200, "OK", '{"key": "value"}', {})
    assert res.json == {"key": "value"}


def test_http_response_as_parser() -> None:
    res = HttpResponse(200, "OK", "some content", {})
    parser = res.as_parser(SourceParser)
    assert isinstance(parser, SourceParser)
    assert parser.content == "some content"


def test_http_response_as_html_parser() -> None:
    res = HttpResponse(200, "OK", "<html></html>", {})
    parser = res.as_html_parser()
    assert isinstance(parser, HtmlParser)


def test_http_response_as_xml_parser() -> None:
    from xcrap.extractor import XmlParser, xpath

    body = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://a</loc></url></urlset>'
    res = HttpResponse(200, "OK", body, {"content-type": "application/xml"})

    parser = res.as_xml_parser()
    stripped = res.as_xml_parser(remove_namespaces=True)
    prefixed = res.as_xml_parser(namespaces={"s": "http://www.sitemaps.org/schemas/sitemap/0.9"})

    assert isinstance(parser, XmlParser)
    assert parser.extract_value(xpath("//loc/text()")) is None
    assert stripped.extract_value(xpath("//loc/text()")) == "https://a"
    assert prefixed.extract_value(xpath("//s:loc/text()")) == "https://a"

import pytest

from xcrap.extractor import HtmlExtractionModel, JsonExtractionModel, css, jmes_path
from xcrap.factory import create_extraction_model


def test_create_html_parsing_model_basic():
    config = {"type": "html", "model": {"title": {"query": css("h1::text"), "default": "N/A"}}}
    allowed_models = {"html": HtmlExtractionModel}

    model = create_extraction_model(config, allowed_models, allowed_extractors={})

    assert isinstance(model, HtmlExtractionModel)
    assert "title" in model.shape
    assert model.shape["title"].query == css("h1::text")
    assert model.shape["title"].default == "N/A"


def test_create_html_parsing_model_with_extractor():
    config = {"type": "html", "model": {"link": {"query": css("a"), "extractor": "attr:href"}}}
    allowed_models = {"html": HtmlExtractionModel}
    allowed_extractors = {"attr": lambda name: lambda el: el.attrib.get(name)}

    model = create_extraction_model(config, allowed_models, allowed_extractors)

    assert model.shape["link"].extractor is not None
    # Test extractor function directly (mocking element)
    mock_el = type("MockEl", (), {"attrib": {"href": "https://test.com"}})
    assert model.shape["link"].extractor(mock_el) == "https://test.com"


def test_create_json_parsing_model():
    config = {"type": "json", "model": {"price": {"query": jmes_path("data.price")}}}
    allowed_models = {"json": JsonExtractionModel}

    model = create_extraction_model(config, allowed_models, allowed_extractors={})

    assert isinstance(model, JsonExtractionModel)
    assert model.shape["price"].query == jmes_path("data.price")


def test_create_nested_parsing_model():
    config = {
        "type": "html",
        "model": {
            "items": {
                "query": css(".item"),
                "multiple": True,
                "nested": {"type": "html", "model": {"name": {"query": css(".name::text")}}},
            }
        },
    }
    allowed_models = {"html": HtmlExtractionModel}

    model = create_extraction_model(config, allowed_models, allowed_extractors={})

    assert "items" in model.shape
    assert model.shape["items"].multiple is True
    assert isinstance(model.shape["items"].model, HtmlExtractionModel)
    assert "name" in model.shape["items"].model.shape


def test_create_json_nested_parsing_model():
    config = {
        "type": "json",
        "model": {"root": {"query": jmes_path("data"), "nested": {"type": "json", "model": {"id": {"query": jmes_path("id")}}}}},
    }
    allowed_models = {"json": JsonExtractionModel}

    model = create_extraction_model(config, allowed_models, allowed_extractors={})

    assert isinstance(model.shape["root"].model, JsonExtractionModel)
    assert model.shape["root"].model.shape["id"].query == jmes_path("id")


def test_create_parsing_model_unsupported_type():
    config = {"type": "unknown", "model": {}}
    with pytest.raises(ValueError, match="Unsupported model type"):
        create_extraction_model(config, {}, {})


def test_create_xml_parsing_model_with_namespaces():
    from xcrap.extractor import XmlBaseField, XmlExtractionModel, XmlNestedField, xpath

    config = {
        "type": "xml",
        "namespaces": {"atom": "http://www.w3.org/2005/Atom"},
        "model": {
            "title": {"query": xpath("/atom:feed/atom:title/text()")},
            "entries": {
                "query": xpath("//atom:entry"),
                "multiple": True,
                "nested": {
                    "type": "xml",
                    "namespaces": {"atom": "http://www.w3.org/2005/Atom"},
                    "model": {"href": {"query": xpath("atom:link"), "extractor": "attr:href"}},
                },
            },
        },
    }
    allowed_extractors = {"attr": lambda name: lambda el: el.attrib.get(name)}

    model = create_extraction_model(config, {"xml": XmlExtractionModel}, allowed_extractors)

    assert isinstance(model, XmlExtractionModel)
    assert isinstance(model.shape["title"], XmlBaseField)
    assert isinstance(model.shape["entries"], XmlNestedField)
    assert model.extract(
        '<feed xmlns="http://www.w3.org/2005/Atom"><title>T</title>'
        '<entry><link href="https://a"/></entry><entry><link href="https://b"/></entry></feed>'
    ) == {"title": "T", "entries": [{"href": "https://a"}, {"href": "https://b"}]}


def test_create_xml_parsing_model_remove_namespaces():
    from xcrap.extractor import XmlExtractionModel, xpath

    config = {"type": "xml", "remove_namespaces": True, "model": {"locs": {"query": xpath("//loc/text()"), "multiple": True}}}

    model = create_extraction_model(config, {"xml": XmlExtractionModel}, allowed_extractors={})

    assert model.extract('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>a</loc></url></urlset>') == {
        "locs": ["a"]
    }


def test_create_parsing_model_rejects_unknown_model_classes():
    from xcrap.extractor.extraction_model import ExtractionModel

    class CustomModel(ExtractionModel):
        def __init__(self, shape=None):
            self.shape = shape

        def extract(self, content):
            return content

    with pytest.raises(ValueError, match="Unsupported model class"):
        create_extraction_model({"type": "custom", "model": {}}, {"custom": CustomModel}, allowed_extractors={})

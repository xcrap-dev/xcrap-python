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

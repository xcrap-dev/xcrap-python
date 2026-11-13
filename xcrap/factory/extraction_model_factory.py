from typing import Any, Dict, Tuple, Type

from ..extractor.extraction_model import ExtractionModel
from ..extractor.html_extraction_model import HtmlBaseField, HtmlExtractionModel, HtmlNestedField
from ..extractor.json_extraction_model import JsonBaseField, JsonExtractionModel, JsonNestedField
from ..extractor.xml_extraction_model import XmlBaseField, XmlExtractionModel, XmlNestedField
from .extractor_factory import create_extractor


def create_extraction_model(
    model_config: Dict[str, Any],
    allowed_models: Dict[str, Type[ExtractionModel]],
    allowed_extractors: Dict[str, Any],
    extractor_argument_separator: str = ":",
) -> ExtractionModel:
    """
    Creates a parsing model instance from a configuration dictionary.

    Args:
        model_config: A dictionary containing the model 'type' and 'model' schema. XML models also
            accept 'namespaces' (prefix -> URI) and 'remove_namespaces'.
        allowed_models: A dictionary mapping model types to ExtractionModel classes.
        allowed_extractors: A dictionary mapping extractor names to their generators.
        extractor_argument_separator: The character used to split extractor keys from arguments.

    Returns:
        An instantiated ExtractionModel (HtmlExtractionModel, JsonExtractionModel or XmlExtractionModel).
    """
    model_type = model_config.get("type")
    if not model_type or model_type not in allowed_models:
        raise ValueError(f"Unsupported model type: '{model_type}'")

    model_class = allowed_models[model_type]
    base_field_class, nested_field_class = _field_classes(model_class)
    fields_config = model_config.get("model", {})
    shape = {}

    for field_name, field_data in fields_config.items():
        extractor = None
        if "extractor" in field_data:
            extractor = create_extractor(field_data["extractor"], allowed_extractors, extractor_argument_separator)

        common = {
            "query": field_data.get("query"),
            "default": field_data.get("default"),
            "multiple": field_data.get("multiple", False),
            "limit": field_data.get("limit"),
        }

        # JSON fields have no extractor: JMESPath already transforms the value
        if base_field_class is not JsonBaseField:
            common["extractor"] = extractor

        if "nested" in field_data:
            nested_model = create_extraction_model(
                field_data["nested"], allowed_models, allowed_extractors, extractor_argument_separator
            )
            shape[field_name] = nested_field_class(model=nested_model, **common)
        else:
            shape[field_name] = base_field_class(**common)

    model_kwargs: Dict[str, Any] = {"shape": shape}

    if issubclass(model_class, XmlExtractionModel):
        model_kwargs["namespaces"] = model_config.get("namespaces")
        model_kwargs["remove_namespaces"] = model_config.get("remove_namespaces")

    return model_class(**model_kwargs)


def _field_classes(model_class: Type[ExtractionModel]) -> Tuple[type, type]:
    if issubclass(model_class, HtmlExtractionModel):
        return HtmlBaseField, HtmlNestedField

    if issubclass(model_class, JsonExtractionModel):
        return JsonBaseField, JsonNestedField

    if issubclass(model_class, XmlExtractionModel):
        return XmlBaseField, XmlNestedField

    raise ValueError(f"Unsupported model class: '{model_class.__name__}'")

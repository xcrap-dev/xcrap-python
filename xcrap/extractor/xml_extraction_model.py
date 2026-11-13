from typing import Any, Callable, ClassVar, Dict, Optional, Type, Union

from parsel import Selector
from pydantic import BaseModel

from .extraction_model import ExtractionModel
from .query_builders import QueryConfig


class XmlBaseField(BaseModel):
    query: QueryConfig
    default: Optional[Any] = None
    multiple: bool = False
    limit: Optional[int] = None
    extractor: Optional[Callable[[Selector], Any]] = None


class XmlNestedField(BaseModel):
    query: Optional[QueryConfig] = None
    model: Union[ExtractionModel, Type[ExtractionModel]]
    limit: Optional[int] = None
    default: Optional[Any] = None
    multiple: bool = False
    extractor: Optional[Callable[[Selector], Any]] = None

    model_config = {"arbitrary_types_allowed": True}


XmlExtractionField = Union[XmlBaseField, XmlNestedField]


def create_xml_selector(
    content: str | bytes,
    namespaces: Optional[Dict[str, str]] = None,
    remove_namespaces: bool = False,
) -> Selector:
    """
    Parses an XML document into a parsel ``Selector`` (entities are not resolved).

    ``namespaces`` registers ``prefix -> URI`` pairs for queries; ``remove_namespaces`` strips every
    namespace from the document so plain names (``//entry``) match namespaced elements.
    """
    if isinstance(content, bytes):
        selector = Selector(body=content, type="xml", namespaces=namespaces)
    else:
        selector = Selector(text=content, type="xml", namespaces=namespaces)

    if remove_namespaces:
        selector.remove_namespaces()

    return selector


class XmlExtractionModel(ExtractionModel):
    """
    Declarative model for XML documents (RSS, Atom, sitemaps, SOAP, ...).

    Same contract as ``HtmlExtractionModel``: ``XmlBaseField`` / ``XmlNestedField`` class attributes
    (merged through inheritance) or a ``shape`` dict, and CSS or XPath queries.
    """

    _fields: Dict[str, XmlExtractionField] = {}
    namespaces: ClassVar[Dict[str, str]] = {}
    remove_namespaces: ClassVar[bool] = False

    def __init__(
        self,
        shape: Optional[Dict[str, XmlExtractionField]] = None,
        namespaces: Optional[Dict[str, str]] = None,
        remove_namespaces: Optional[bool] = None,
    ) -> None:
        self.shape = shape if shape is not None else self._fields
        self.namespaces = {**type(self).namespaces, **(namespaces or {})}
        self.remove_namespaces = type(self).remove_namespaces if remove_namespaces is None else remove_namespaces

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        fields = {}

        for name, attr in cls.__dict__.items():
            if isinstance(attr, (XmlBaseField, XmlNestedField)):
                fields[name] = attr

        combined_fields = {}

        for base in reversed(cls.__mro__):
            if hasattr(base, "_fields"):
                combined_fields.update(base._fields)

        combined_fields.update(fields)

        cls._fields = combined_fields

    def extract(self, content: str | bytes | Selector) -> Dict[str, Any]:
        if isinstance(content, Selector):
            root = content

            for prefix, uri in self.namespaces.items():
                root.register_namespace(prefix, uri)
        else:
            root = create_xml_selector(content, self.namespaces, self.remove_namespaces)

        data: Dict[str, Any] = {}

        for key, value in self.shape.items():
            if isinstance(value, XmlNestedField):
                data[key] = self._extract_nested_value(value, root)

            else:
                data[key] = self._extract_base_value(value, root)

        return data

    def _extract_base_value(self, value: XmlBaseField, root: Selector) -> Any:
        elements = self._select_elements(value.query, root)

        if value.multiple:
            if value.limit is not None:
                elements = elements[: value.limit]

            if value.extractor:
                results = [value.extractor(el) for el in elements]
            else:
                results = elements.getall()

            return results if results else (value.default if value.default is not None else [])

        if len(elements) == 0:
            return value.default

        element = elements[0]

        if value.extractor:
            return value.extractor(element)

        return element.get()

    def _extract_nested_value(self, value: XmlNestedField, root: Selector) -> Any:
        model = value.model

        if isinstance(model, type):
            model = model()

        if value.multiple:
            if value.query is None:
                raise ValueError("Query is required for nested model with multiple values")

            elements = self._select_elements(value.query, root)

            if value.limit is not None:
                elements = elements[: value.limit]

            results = [model.extract(el) for el in elements]

            return results if results else (value.default if value.default is not None else [])

        elements = self._select_elements(value.query, root) if value.query else [root]

        if len(elements) == 0:
            return value.default

        element = elements[0]
        source = value.extractor(element) if value.extractor else element

        return model.extract(source)

    def _select_elements(self, query: QueryConfig, root: Selector):
        if query["type"] == "css":
            return root.css(query["value"])

        return root.xpath(query["value"], namespaces=self.namespaces or None)


__all__ = [
    "XmlBaseField",
    "XmlNestedField",
    "XmlExtractionModel",
    "XmlExtractionField",
    "create_xml_selector",
]

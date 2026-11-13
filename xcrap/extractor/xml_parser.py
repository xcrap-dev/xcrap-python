from typing import Any, Dict, Optional

from parsel import Selector

from .extraction_model import ExtractionModel
from .query_builders import QueryConfig
from .source_parser import SourceParser
from .xml_extraction_model import create_xml_selector


class XmlParser(SourceParser):
    """
    Parses XML documents (RSS, Atom, sitemaps, ...) and queries them with CSS or XPath.
    """

    def __init__(
        self,
        content: str | bytes,
        namespaces: Optional[Dict[str, str]] = None,
        remove_namespaces: bool = False,
    ) -> None:
        super().__init__(content)
        self.namespaces = dict(namespaces or {})
        self.selector = create_xml_selector(content, self.namespaces, remove_namespaces)

    @property
    def root(self) -> Selector:
        return self.selector

    def extract_value(self, query: QueryConfig, default: Optional[Any] = None) -> Any:
        result = self._select_elements(query).get()

        return result if result is not None else default

    def extract_values(self, query: QueryConfig, limit: Optional[int] = None) -> list[str]:
        elements = self._select_elements(query)

        if limit is not None:
            elements = elements[:limit]

        return elements.getall()

    def extract_model(
        self,
        model: ExtractionModel | type[ExtractionModel],
        query: Optional[QueryConfig] = None,
    ) -> Any:
        """Runs a model over the whole document, or over the first match of ``query`` (``None`` if nothing matches)."""
        if query is None:
            element = self.selector
        else:
            elements = self._select_elements(query)

            if len(elements) == 0:
                return None

            element = elements[0]

        return self._instantiate(model).extract(element)

    def extract_models(
        self,
        model: ExtractionModel | type[ExtractionModel],
        query: QueryConfig,
        limit: Optional[int] = None,
    ) -> list[Any]:
        elements = self._select_elements(query)

        if limit is not None:
            elements = elements[:limit]

        instance = self._instantiate(model)

        return [instance.extract(element) for element in elements]

    @staticmethod
    def _instantiate(model: ExtractionModel | type[ExtractionModel]) -> ExtractionModel:
        return model() if isinstance(model, type) else model

    def _select_elements(self, query: QueryConfig):
        if query["type"] == "css":
            return self.selector.css(query["value"])

        return self.selector.xpath(query["value"])


__all__ = ["XmlParser"]

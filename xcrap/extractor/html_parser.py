from typing import Any, Optional

from parsel import Selector

from .html_extraction_model import HtmlExtractionModel
from .query_builders import QueryConfig
from .source_parser import SourceParser


class HtmlParser(SourceParser):
    def __init__(self, content: str) -> None:
        self.selector = Selector(text=content)

    @property
    def root(self) -> Selector:
        return self.selector

    def extract_value(self, query: QueryConfig, default: Optional[str] = None) -> Optional[str]:
        elements = self._select_elements(query)
        result = elements.get()

        return result if result is not None else default

    def extract_values(self, query: QueryConfig, limit: Optional[int] = None) -> list[str]:
        elements = self._select_elements(query)

        if limit is not None:
            elements = elements[:limit]

        return elements.getall()

    def extract_model(self, model: type[HtmlExtractionModel], query: Optional[QueryConfig] = None) -> Any:
        element = self._select_elements(query)[0] if query else self.selector

        return model().extract(element)

    def extract_models(
        self,
        model: type[HtmlExtractionModel],
        query: QueryConfig,
        limit: Optional[int] = None,
    ) -> list[Any]:
        elements = self._select_elements(query)

        if limit is not None:
            elements = elements[:limit]

        return [model().extract(el) for el in elements]

    def _select_elements(self, query: QueryConfig):
        if query["type"] == "css":
            return self.selector.css(query["value"])

        return self.selector.xpath(query["value"])

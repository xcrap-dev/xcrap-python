import json
from typing import Any, Optional

import jmespath

from .json_extraction_model import JsonExtractionModel
from .query_builders import QueryConfig
from .source_parser import SourceParser


class JsonParser(SourceParser):
    def __init__(self, content: str) -> None:
        super().__init__(content)
        self.data = json.loads(content)

    def extract_value(self, query: QueryConfig, default: Optional[Any] = None) -> Any:
        result = jmespath.search(query["value"], self.data)
        return result if result is not None else default

    def extract_values(self, query: QueryConfig, limit: Optional[int] = None) -> list[Any]:
        results = jmespath.search(query["value"], self.data)

        if not isinstance(results, list):
            results = [results] if results is not None else []

        if limit is not None:
            results = results[:limit]

        return results

    def extract_model(self, model: type[JsonExtractionModel], query: Optional[QueryConfig] = None) -> Any:
        element = jmespath.search(query["value"], self.data) if query else self.data

        return model().extract(element)

    def extract_models(
        self,
        model: type[JsonExtractionModel],
        query: QueryConfig,
        limit: Optional[int] = None,
    ) -> list[Any]:
        elements = jmespath.search(query["value"], self.data)

        if not isinstance(elements, list):
            elements = [elements] if elements is not None else []

        if limit is not None:
            elements = elements[:limit]

        return [model().extract(el) for el in elements]

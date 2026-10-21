import re
from typing import Any, Callable, Optional, TypedDict

from ..core.errors import (
    InvalidPageValueError,
    InvalidUrlError,
    PageOutOfRangeError,
    PageParsingFailureError,
)
from ..extractor.query_builders import QueryConfig


class Tracker(TypedDict, total=False):
    query: QueryConfig
    extractor: Optional[Callable[[Any], Any]]
    transformer: Optional[Callable[[Any], int]]


class Trackers(TypedDict):
    current_page: Tracker
    last_page: Tracker


class StaticPaginator:
    """
    Manages static pagination, URL generation with '{page}' templates, and page tracking.
    """

    def __init__(
        self,
        initial_page: int,
        last_page: int,
        template_url: str,
        min_page: Optional[int] = None,
    ) -> None:
        self.initial_page = initial_page
        self.last_page = last_page
        self.min_page = min_page if min_page is not None else initial_page
        self.template_url = template_url
        self.current_page = initial_page

        # Validate template URL
        self.generate_url(template_url, initial_page)

    @staticmethod
    def generate_url(url: str, page: int) -> str:
        """
        Replaces the '{page}' placeholder in the given URL with the target page number.
        """
        if "{page}" not in url:
            raise InvalidUrlError(url)
        return url.replace("{page}", str(page))

    def set(self, page: int) -> str:
        """Sets the current page number and returns its URL."""
        if page < self.min_page or page > self.last_page:
            raise PageOutOfRangeError(page, self.min_page, self.last_page)
        self.current_page = page
        return self.current

    def previous(self) -> str:
        """Decrements the current page and returns its URL."""
        if self.current_page <= self.min_page:
            raise PageOutOfRangeError(self.current_page - 1, self.min_page, self.last_page)
        self.current_page -= 1
        return self.current

    @property
    def current(self) -> str:
        """Returns the URL corresponding to the current page."""
        return self.generate_url(self.template_url, self.current_page)

    def next(self) -> str:
        """Increments the current page and returns its URL."""
        if self.current_page >= self.last_page:
            raise PageOutOfRangeError(self.current_page + 1, self.min_page, self.last_page)
        self.current_page += 1
        return self.current

    def dump(self, limit: Optional[int] = None) -> list[str]:
        """
        Generates and returns a list of URLs from the current page up to last_page
        (optionally capped by limit).
        """
        max_page = min(self.last_page, self.current_page + limit - 1) if limit is not None else self.last_page
        return [self.generate_url(self.template_url, page) for page in range(self.current_page, max_page + 1)]

    @classmethod
    async def create_with_tracking(
        cls,
        client: Any,
        request: Any,
        template_url: str,
        trackers: Trackers,
    ) -> dict[str, Any]:
        """
        Executes a request via client, parses current and last page numbers
        using trackers, and instantiates a StaticPaginator.
        """
        if isinstance(request, str):
            response = await client.fetch(url=request)
        elif isinstance(request, dict):
            response = await client.fetch(**request)
        else:
            response = await client.fetch(request)

        parser = response.as_html_parser()

        def _extract_page(tracker: Tracker) -> int:
            query = tracker.get("query")
            if not query:
                raise PageParsingFailureError("Tracker query is missing.")

            # Select element
            elements = parser._select_elements(query)

            if not elements:
                raise PageParsingFailureError("No matching elements found for tracker query.")

            extractor = tracker.get("extractor")
            raw_val = extractor(elements[0]) if extractor else elements[0].get()
            if raw_val is None:
                raise PageParsingFailureError("Extracted raw value is None.")

            transformer = tracker.get("transformer")
            if transformer:
                try:
                    return int(transformer(raw_val))
                except Exception as exc:
                    raise InvalidPageValueError(f"Transformer failed: {exc}") from exc

            # Default conversion
            if isinstance(raw_val, (int, float)):
                return int(raw_val)

            match = re.search(r"\d+", str(raw_val))
            if not match:
                raise InvalidPageValueError(f"Could not parse integer from '{raw_val}'.")
            return int(match.group(0))

        current_p = _extract_page(trackers["current_page"])
        last_p = _extract_page(trackers["last_page"])

        return {
            "response": response,
            "parser": parser,
            "paginator": cls(
                initial_page=current_p,
                last_page=last_p,
                template_url=template_url,
            ),
        }


__all__ = ["StaticPaginator", "Tracker", "Trackers"]

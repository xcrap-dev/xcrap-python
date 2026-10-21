import json
from typing import Optional, TypedDict, TypeVar

from ..extractor.html_parser import HtmlParser
from ..extractor.source_parser import SourceParser

SourceParserType = TypeVar("SourceParserType", bound=SourceParser)


class FailedAttempt(TypedDict):
    timestamp: int
    error: str


class HttpResponse:
    def __init__(
        self,
        status: int,
        status_text: str,
        body: str,
        headers: dict[str, str],
        attempts: Optional[int] = None,
        failed_attempts: Optional[list[FailedAttempt]] = None,
    ) -> None:
        self.status = status
        self.status_text = status_text
        self.body = body
        self.headers = {k.lower(): v for k, v in headers.items()}
        self.attempts = attempts
        self.failed_attempts = failed_attempts

    def is_success(self) -> bool:
        return 200 <= self.status < 300

    def get_header(self, name: str) -> Optional[str]:
        return self.headers.get(name.lower())

    @property
    def text(self) -> str:
        return self.body

    @property
    def json(self) -> dict:
        return json.loads(self.body)

    def as_parser(self, parser: type[SourceParserType]) -> SourceParserType:
        return parser(self.body)

    def as_html_parser(self) -> HtmlParser:
        return HtmlParser(self.body)

    def as_json_parser(self):
        from ..extractor.json_parser import JsonParser
        return JsonParser(self.body)

    def as_markdown_parser(self):
        from ..extractor.markdown_parser import MarkdownParser
        return MarkdownParser(self.body)


__all__ = [
    "HttpResponse",
    "FailedAttempt",
]

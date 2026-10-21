from typing import Any, Iterable, Optional
from urllib.parse import urljoin

from ..core.http_response import HttpResponse
from .request import Callback, Request


class SpiderResponse(HttpResponse):
    """An `HttpResponse` that remembers the `Request` which produced it."""

    def __init__(self, request: Request, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.request = request

    @classmethod
    def from_http(cls, response: HttpResponse, request: Request) -> "SpiderResponse":
        return cls(
            request=request,
            status=response.status,
            status_text=response.status_text,
            body=response.body,
            headers=response.headers,
            attempts=response.attempts,
            failed_attempts=response.failed_attempts,
        )

    @property
    def url(self) -> str:
        return self.request.url

    @property
    def meta(self) -> dict[str, Any]:
        return self.request.meta

    def urljoin(self, url: str) -> str:
        return urljoin(self.url, url)

    def follow(
        self,
        url: str,
        callback: Optional[Callback] = None,
        **kwargs: Any,
    ) -> Request:
        """Builds a `Request` for a (possibly relative) URL, reusing this request's callback by default."""
        return Request(
            url=self.urljoin(url),
            callback=callback if callback is not None else self.request.callback,
            **kwargs,
        )

    def follow_all(
        self,
        urls: Iterable[str],
        callback: Optional[Callback] = None,
        **kwargs: Any,
    ) -> list[Request]:
        return [self.follow(url, callback, **kwargs) for url in urls]


__all__ = ["SpiderResponse"]

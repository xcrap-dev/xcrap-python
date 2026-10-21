from dataclasses import dataclass, field, replace
from typing import Any, Callable, Optional, Union

Callback = Union[Callable[..., Any], str]


@dataclass
class Request:
    """
    A unit of work scheduled by a spider.

    `callback` and `errback` may be a callable or the name of a spider method.
    `max_retries` / `retry_delay` (ms) fall back to the spider defaults and are executed by the HTTP client itself.
    """

    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    callback: Optional[Callback] = None
    errback: Optional[Callback] = None
    meta: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    dont_filter: bool = False
    max_retries: Optional[int] = None
    retry_delay: Optional[int] = None
    depth: Optional[int] = None

    def replace(self, **changes: Any) -> "Request":
        return replace(self, **changes)


__all__ = ["Request", "Callback"]

import asyncio
import itertools
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .request import Request


def fingerprint(request: Request) -> str:
    """Method + URL with sorted query string and no fragment."""
    parts = urlsplit(request.url)
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    url = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, query, ""))

    return f"{request.method.upper()} {url}"


class Scheduler:
    """Priority queue (higher `priority` first, FIFO within the same priority) with duplicate filtering."""

    def __init__(self, dedupe: bool = True) -> None:
        self.dedupe = dedupe
        self._queue: asyncio.PriorityQueue[tuple[int, int, Request]] = asyncio.PriorityQueue()
        self._seen: set[str] = set()
        self._counter = itertools.count()

    def is_duplicate(self, request: Request) -> bool:
        if not self.dedupe or request.dont_filter:
            return False

        return fingerprint(request) in self._seen

    def push(self, request: Request) -> None:
        if self.dedupe and not request.dont_filter:
            self._seen.add(fingerprint(request))

        self._queue.put_nowait((-request.priority, next(self._counter), request))

    async def pop(self) -> Request:
        _, _, request = await self._queue.get()

        return request

    def done(self) -> None:
        self._queue.task_done()

    async def join(self) -> None:
        await self._queue.join()


__all__ = ["Scheduler", "fingerprint"]

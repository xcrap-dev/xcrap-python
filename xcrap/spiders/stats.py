import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SpiderStats:
    requests_scheduled: int = 0
    requests_made: int = 0
    requests_failed: int = 0
    requests_filtered: int = 0
    requests_dropped: int = 0
    items_scraped: int = 0
    items_dropped: int = 0
    callback_errors: int = 0
    pipeline_errors: int = 0
    status_counts: dict[int, int] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None

    @property
    def elapsed(self) -> float:
        return (self.finished_at or time.time()) - self.started_at


__all__ = ["SpiderStats"]

import random
from typing import Generic, Optional, Sequence, TypeVar

from ..core.errors import EmptyListError

T = TypeVar("T")

# Modern, real-world desktop user agents across popular browsers and operating systems
MODERN_USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.3; rv:123.0) Gecko/20100101 Firefox/123.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]


class Randomizer(Generic[T]):
    """
    Picks random items from a collection and provides realistic modern User-Agent generators.
    """

    def __init__(self, values: Sequence[T]) -> None:
        if not values:
            raise EmptyListError(self.__class__.__name__)
        self._values: list[T] = list(values)

    @property
    def values(self) -> list[T]:
        return self._values

    def random(self) -> T:
        """Picks and returns a random element from the collection."""
        return random.choice(self._values)

    @classmethod
    def user_agent(cls, browser: Optional[str] = None) -> str:
        """
        Returns a random, realistic modern User-Agent string.
        Optionally filter by browser type ('chrome', 'firefox', 'safari', 'edge').
        """
        if browser:
            filtered = [ua for ua in MODERN_USER_AGENTS if browser.lower() in ua.lower()]
            if filtered:
                return random.choice(filtered)
        return random.choice(MODERN_USER_AGENTS)


__all__ = ["Randomizer", "MODERN_USER_AGENTS"]

from typing import Generic, Sequence, TypeVar

from ..core.errors import EmptyListError

T = TypeVar("T")


class Rotator(Generic[T]):
    """
    Manages cyclical or sequential rotation over a list of items (e.g. proxies, user-agents, tokens).
    """

    def __init__(self, values: Sequence[T]) -> None:
        if not values:
            raise EmptyListError(self.__class__.__name__)
        self._values: list[T] = list(values)
        self._current_index: int = 0

    @property
    def values(self) -> list[T]:
        return self._values

    @property
    def current(self) -> T:
        """Returns the current element without advancing the pointer."""
        return self._values[self._current_index]

    def rotate(self) -> T:
        """Advances to the next element and returns it."""
        self._current_index = (self._current_index + 1) % len(self._values)
        return self._values[self._current_index]

    def next(self) -> T:
        """Alias for rotate(). Advances to the next element."""
        return self.rotate()

    def reset(self) -> None:
        """Resets the rotator index back to the beginning."""
        self._current_index = 0

    def __iter__(self):
        return self

    def __next__(self) -> T:
        val = self.current
        self.rotate()
        return val

    def __len__(self) -> int:
        return len(self._values)


__all__ = ["Rotator"]

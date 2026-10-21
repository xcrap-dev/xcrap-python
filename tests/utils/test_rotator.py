import pytest

from xcrap.core.errors import EmptyListError
from xcrap.utils.rotator import Rotator


def test_rotator_initialization():
    rotator = Rotator(["a", "b", "c"])
    assert rotator.values == ["a", "b", "c"]
    assert rotator.current == "a"
    assert len(rotator) == 3


def test_rotator_empty_list_raises_error():
    with pytest.raises(EmptyListError) as exc_info:
        Rotator([])
    assert "Rotator cannot receive empty lists" in str(exc_info.value)


def test_rotator_rotate_and_next():
    rotator = Rotator(["first", "second", "third"])
    assert rotator.current == "first"

    next_val = rotator.rotate()
    assert next_val == "second"
    assert rotator.current == "second"

    next_val_2 = rotator.next()
    assert next_val_2 == "third"
    assert rotator.current == "third"

    # Cycles back to beginning
    cycled_val = rotator.rotate()
    assert cycled_val == "first"
    assert rotator.current == "first"


def test_rotator_reset():
    rotator = Rotator([1, 2, 3])
    rotator.next()
    rotator.next()
    assert rotator.current == 3

    rotator.reset()
    assert rotator.current == 1


def test_rotator_iterator_protocol():
    rotator = Rotator(["alpha", "beta"])
    iterator = iter(rotator)

    assert next(iterator) == "alpha"
    assert next(iterator) == "beta"
    assert next(iterator) == "alpha"

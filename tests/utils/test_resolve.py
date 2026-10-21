from xcrap.utils.resolve import resolve


def test_resolve_should_resolve_fn() -> None:
    def fn() -> int:
        return 0

    expected = 0
    data = resolve(fn)

    assert data == expected


def test_resolve_should_return_value() -> None:
    input = 0
    expected = 0
    data = resolve(input)

    assert data == expected


def test_resolve_should_return_none() -> None:
    input = None
    expected = None
    data = resolve(input)

    assert data == expected

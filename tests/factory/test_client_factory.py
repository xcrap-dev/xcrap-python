import pytest

from xcrap.core.http_client_base import HttpClientBase
from xcrap.factory import create_client


class MockClient(HttpClientBase):
    def __init__(self, some_opt=None, **kwargs):
        super().__init__(**kwargs)
        self.some_opt = some_opt

    async def fetch(self, *args, **kwargs):
        pass

    async def fetch_many(self, *args, **kwargs):
        pass


def test_create_client_success():
    allowed = {"mock": MockClient}
    opts = {"some_opt": "value", "user_agent": "test-agent"}

    client = create_client("mock", allowed, opts)

    assert isinstance(client, MockClient)
    assert client.some_opt == "value"
    assert client.user_agent == "test-agent"  # from BaseClient


def test_create_client_invalid_type():
    with pytest.raises(ValueError, match="not a valid type of client"):
        create_client("invalid", {}, {})


def test_create_extractor_with_args():
    from xcrap.factory.extractor_factory import create_extractor

    allowed = {"split": lambda sep: lambda el: el.text.split(sep)}

    extractor = create_extractor("split| ", allowed, argument_separator="|")

    mock_el = type("MockEl", (), {"text": "hello world"})
    assert extractor(mock_el) == ["hello", "world"]


def test_create_extractor_invalid_key():
    from xcrap.factory.extractor_factory import create_extractor

    with pytest.raises(ValueError, match="not an allowed extractor"):
        create_extractor("missing", {}, ":")


def test_create_extractor_invalid_key_with_args():
    from xcrap.factory.extractor_factory import create_extractor

    with pytest.raises(ValueError, match="not an allowed extractor"):
        create_extractor("missing:arg", {}, ":")


def test_create_extractor_no_args():
    from xcrap.factory.extractor_factory import create_extractor

    allowed = {"mock": lambda: lambda el: "extracted"}
    extractor = create_extractor("mock", allowed)
    assert extractor(None) == "extracted"

import pytest

from xcrap.core.errors import EmptyListError
from xcrap.utils.randomizer import MODERN_USER_AGENTS, Randomizer


def test_randomizer_initialization():
    items = ["item1", "item2", "item3"]
    randomizer = Randomizer(items)
    assert randomizer.values == items


def test_randomizer_empty_list_raises_error():
    with pytest.raises(EmptyListError) as exc_info:
        Randomizer([])
    assert "Randomizer cannot receive empty lists" in str(exc_info.value)


def test_randomizer_random_choice():
    items = ["apple", "banana", "cherry"]
    randomizer = Randomizer(items)

    chosen = randomizer.random()
    assert chosen in items


def test_randomizer_user_agent():
    ua = Randomizer.user_agent()
    assert isinstance(ua, str)
    assert ua in MODERN_USER_AGENTS


def test_randomizer_user_agent_filtered():
    chrome_ua = Randomizer.user_agent(browser="chrome")
    assert "chrome" in chrome_ua.lower()

    firefox_ua = Randomizer.user_agent(browser="firefox")
    assert "firefox" in firefox_ua.lower()

    # Fallback to random if browser not found
    unknown_ua = Randomizer.user_agent(browser="nonexistent_browser_xyz")
    assert unknown_ua in MODERN_USER_AGENTS

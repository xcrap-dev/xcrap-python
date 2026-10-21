import importlib.util
import pathlib
import sys
from unittest.mock import patch

import pytest

import xcrap
from xcrap.core.errors import DependencyMissingError

ROOT = pathlib.Path(xcrap.__file__).parent


def load_without(relative_path: str, blocked: list[str]):
    """Executes a throwaway copy of a module while `blocked` packages cannot be imported."""
    name = "xcrap." + relative_path[:-3].replace("/", ".") + "_without_deps"
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)

    with patch.dict(sys.modules, {package: None for package in blocked}):
        spec.loader.exec_module(module)

    return module


def test_curl_cffi_import_fallback():
    module = load_without("clients/curl_cffi.py", ["curl_cffi", "curl_cffi.requests"])
    assert module.AsyncSession is None

    with pytest.raises(DependencyMissingError):
        module.CurlCffiClient()


def test_playwright_import_fallback():
    module = load_without("clients/playwright.py", ["playwright", "playwright.async_api"])
    assert module.async_playwright is None

    with pytest.raises(DependencyMissingError):
        module.PlaywrightClient()


def test_selenium_import_fallback():
    module = load_without("clients/selenium.py", ["selenium"])
    assert module.webdriver is None

    with pytest.raises(DependencyMissingError):
        module.SeleniumClient()


def test_seleniumbase_import_fallback():
    module = load_without("clients/seleniumbase.py", ["seleniumbase"])
    assert module.Driver is None

    with pytest.raises(DependencyMissingError):
        module.SeleniumBaseClient()


def test_markdown_import_fallback():
    module = load_without("extractor/markdown_parser.py", ["markdown"])
    assert module.md_lib is None

    with pytest.raises(DependencyMissingError):
        module.render_markdown_to_html("# title")

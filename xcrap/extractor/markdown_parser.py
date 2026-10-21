import html
from typing import Optional

try:
    import markdown as md_lib
except ImportError:
    md_lib = None

from ..core.errors import DependencyMissingError
from .html_parser import HtmlParser


def render_markdown_to_html(source: str) -> str:
    """
    Renders raw Markdown string into an HTML document.
    """
    if md_lib is None:
        raise DependencyMissingError(package_name="markdown", extra_name="markdown")

    rendered = md_lib.markdown(
        source,
        extensions=["extra", "tables", "fenced_code", "toc", "sane_lists"],
    )
    decoded = html.unescape(rendered).replace("\u00a0", " ")
    return (
        f"<!DOCTYPE html><html lang=\"en\"><head><title>Markdown Document</title></head>"
        f"<body>{decoded}</body></html>"
    )


class MarkdownParser(HtmlParser):
    """
    Parses Markdown documents by converting them to HTML and wrapping them in Parsel selectors.
    """

    def __init__(self, source: str) -> None:
        html_doc = render_markdown_to_html(source)
        super().__init__(html_doc)
        self.markdown_source: str = source


__all__ = ["MarkdownParser", "render_markdown_to_html"]

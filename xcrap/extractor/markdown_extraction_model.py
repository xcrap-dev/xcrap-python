from typing import Any, Dict, Optional

from parsel import Selector

from .html_extraction_model import HtmlExtractionField, HtmlExtractionModel
from .markdown_parser import render_markdown_to_html


class MarkdownExtractionModel(HtmlExtractionModel):
    """
    Declarative model for extracting structured data directly from Markdown documents.
    """

    def __init__(self, shape: Optional[Dict[str, HtmlExtractionField]] = None) -> None:
        super().__init__(shape=shape)

    def extract(self, content: str | Selector) -> Dict[str, Any]:
        if isinstance(content, str):
            html_content = render_markdown_to_html(content)
            return super().extract(html_content)
        return super().extract(content)


__all__ = ["MarkdownExtractionModel"]

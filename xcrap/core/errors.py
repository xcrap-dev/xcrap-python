class XcrapError(Exception):
    """Base exception for all Xcrap errors."""

    pass


class DependencyMissingError(ImportError, XcrapError):
    """Raised when an optional dependency required for an extra feature is missing."""

    def __init__(self, package_name: str, extra_name: str) -> None:
        super().__init__(
            f"The '{package_name}' package is required to use this feature. Install it with: pip install xcrap[{extra_name}]"
        )
        self.package_name = package_name
        self.extra_name = extra_name


class EmptyListError(XcrapError):
    """Raised when an empty list or collection is passed where non-empty is required."""

    def __init__(self, class_name: str) -> None:
        super().__init__(f"{class_name} cannot receive empty lists.")
        self.class_name = class_name


class StaticPaginatorError(XcrapError):
    """Base exception for static paginator operations."""

    pass


class InvalidUrlError(StaticPaginatorError):
    """Raised when a paginator URL template does not contain '{page}'."""

    def __init__(self, url: str) -> None:
        super().__init__(f"The provided URL does not contain the placeholder '{{page}}': {url}")
        self.url = url


class PageOutOfRangeError(StaticPaginatorError):
    """Raised when a requested page is outside allowed bounds."""

    def __init__(self, page: int, min_page: int, last_page: int) -> None:
        super().__init__(f"Page {page} is outside the allowed range [{min_page}, {last_page}].")
        self.page = page
        self.min_page = min_page
        self.last_page = last_page


class TrackingError(XcrapError):
    """Base exception for automatic tracking failures in pagination."""

    pass


class PageParsingFailureError(TrackingError):
    """Raised when current or last page numbers cannot be parsed from the response."""

    def __init__(self, message: str = "Failed to parse current or last page from the response.") -> None:
        super().__init__(message)


class InvalidPageValueError(TrackingError):
    """Raised when parsed page numbers cannot be converted to valid integers."""

    def __init__(self, message: str = "Parsed page values are not valid numbers.") -> None:
        super().__init__(message)


class InvalidMarkdownBody(XcrapError):
    """Raised when Markdown content cannot be parsed."""

    def __init__(self, message: str = "Invalid Markdown body.") -> None:
        super().__init__(message)


class DropItem(XcrapError):
    """Raised by an item pipeline to discard the current item."""

    def __init__(self, reason: str = "Item dropped.") -> None:
        super().__init__(reason)
        self.reason = reason


__all__ = [
    "XcrapError",
    "DropItem",
    "DependencyMissingError",
    "EmptyListError",
    "StaticPaginatorError",
    "InvalidUrlError",
    "PageOutOfRangeError",
    "TrackingError",
    "PageParsingFailureError",
    "InvalidPageValueError",
    "InvalidMarkdownBody",
]

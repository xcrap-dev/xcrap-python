import io
from pathlib import Path
from typing import Any, Callable, Union

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

try:
    import pytesseract
except ImportError:
    pytesseract = None  # type: ignore

from ..core.errors import DependencyMissingError


def extract_image_text(
    image: Union[str, Path, bytes, Any],
    lang: str = "eng",
    config: str = "",
) -> str:
    """
    Extracts text from an image using Tesseract OCR.
    Accepts a file path, bytes, or PIL Image instance.
    Requires 'pytesseract' and 'pillow': pip install xcrap[ocr]
    """
    if Image is None or pytesseract is None:
        raise DependencyMissingError(package_name="pytesseract and pillow", extra_name="ocr")

    if isinstance(image, (str, Path)):
        pil_img = Image.open(image)
    elif isinstance(image, bytes):
        pil_img = Image.open(io.BytesIO(image))
    elif hasattr(image, "save") or (isinstance(getattr(Image, "Image", None), type) and isinstance(image, Image.Image)):
        pil_img = image
    else:
        raise ValueError(f"Unsupported image type: {type(image)}")

    text = pytesseract.image_to_string(pil_img, lang=lang, config=config)
    return text.strip()


def image_text_extractor(
    lang: str = "eng",
    config: str = "",
) -> Callable[[Any], str]:
    """
    Factory creating an extractor callable to be used inside HtmlBaseField.
    Accepts element, attribute value (URL/base64/path), or bytes.
    """

    def _extractor(val: Any) -> str:
        # If val is a Parsel Selector, try extracting src or value
        if hasattr(val, "attrib"):
            src = val.attrib.get("src") or val.attrib.get("data-src") or val.get()
            return extract_image_text(src, lang=lang, config=config)
        return extract_image_text(val, lang=lang, config=config)

    return _extractor


__all__ = ["extract_image_text", "image_text_extractor"]

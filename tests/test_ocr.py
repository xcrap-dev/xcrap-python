from unittest.mock import MagicMock, patch
import pytest

from xcrap.core.errors import DependencyMissingError
from xcrap.ocr import extract_image_text, image_text_extractor


def test_ocr_missing_dependencies():
    with patch("xcrap.ocr.Image", None):
        with pytest.raises(DependencyMissingError) as exc_info:
            extract_image_text("fake_path.png")
        assert "ocr" in str(exc_info.value)

    with patch("xcrap.ocr.pytesseract", None):
        with pytest.raises(DependencyMissingError):
            extract_image_text(b"fake_bytes")


def test_ocr_extract_image_text_mocked():
    mock_image = MagicMock()
    mock_pil = MagicMock()
    mock_pil.open.return_value = mock_image

    mock_tesseract = MagicMock()
    mock_tesseract.image_to_string.return_value = "  +55 11 99999-9999  \n"

    with patch("xcrap.ocr.Image", mock_pil), patch("xcrap.ocr.pytesseract", mock_tesseract):
        text = extract_image_text("path/to/phone.png")
        assert text == "+55 11 99999-9999"

        # Test with bytes
        text_from_bytes = extract_image_text(b"image_bytes")
        assert text_from_bytes == "+55 11 99999-9999"

        # Test with direct PIL Image
        text_from_pil = extract_image_text(mock_image)
        assert text_from_pil == "+55 11 99999-9999"


def test_ocr_unsupported_type():
    mock_pil = MagicMock()
    mock_tesseract = MagicMock()

    with patch("xcrap.ocr.Image", mock_pil), patch("xcrap.ocr.pytesseract", mock_tesseract):
        with pytest.raises(ValueError) as exc_info:
            extract_image_text(12345)
        assert "Unsupported image type" in str(exc_info.value)


def test_ocr_image_text_extractor_helper():
    mock_pil = MagicMock()
    mock_tesseract = MagicMock()
    mock_tesseract.image_to_string.return_value = "123456"

    with patch("xcrap.ocr.Image", mock_pil), patch("xcrap.ocr.pytesseract", mock_tesseract):
        extractor_fn = image_text_extractor(lang="eng")

        # Mock a parsel element
        mock_el = MagicMock()
        mock_el.attrib = {"src": "https://example.com/captcha.png"}

        result = extractor_fn(mock_el)
        assert result == "123456"

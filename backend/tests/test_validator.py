from unittest.mock import PropertyMock, patch
from backend.core.config import Settings, settings
from backend.pdf.validator import PdfValidator


def test_validate_valid_28_page_pdf(sample_valid_pdf):
    result = PdfValidator.validate(sample_valid_pdf)
    assert result["valid"] is True
    assert result["pages"] == 28
    assert result["size_bytes"] == len(sample_valid_pdf)
    assert "pdf_version" in result


def test_validate_valid_single_page_pdf(sample_single_page_pdf):
    result = PdfValidator.validate(sample_single_page_pdf)
    assert result["valid"] is True
    assert result["pages"] == 1


def test_validate_empty_file():
    result = PdfValidator.validate(b"")
    assert result["valid"] is False
    assert result["pages"] == 0
    assert "vacío" in result["error"].lower()


def test_validate_html_file(sample_html):
    result = PdfValidator.validate(sample_html)
    assert result["valid"] is False
    assert result["pages"] == 0


def test_validate_json_file(sample_json):
    result = PdfValidator.validate(sample_json)
    assert result["valid"] is False
    assert result["pages"] == 0


def test_validate_corrupted_pdf(sample_corrupted_pdf):
    result = PdfValidator.validate(sample_corrupted_pdf)
    assert result["valid"] is False
    assert result["pages"] == 0


def test_validate_unnormalized_obfuscated_file_fails(sample_obfuscated_pdf):
    # Proves that without the normalizer, the obfuscated PDF fails validation
    result = PdfValidator.validate(sample_obfuscated_pdf)
    assert result["valid"] is False
    assert result["pages"] == 0


def test_validate_oversized_pdf(sample_valid_pdf):
    # Mock settings.max_pdf_size_bytes to be smaller than sample_valid_pdf
    with patch.object(Settings, "max_pdf_size_bytes", new_callable=PropertyMock, return_value=len(sample_valid_pdf) - 1):
        result = PdfValidator.validate(sample_valid_pdf)
        assert result["valid"] is False
        assert result["pages"] == 0
        assert "excede el tamaño" in result["error"].lower()

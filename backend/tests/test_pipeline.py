import pytest
from backend.pdf.default_normalizer import DefaultNormalizer, PassthroughNormalizer
from backend.pdf.processor import PdfProcessor, InvalidPdfError


def test_full_pipeline_on_valid_pdf(sample_valid_pdf, tmp_path):
    output_pdf = tmp_path / "final_valid.pdf"
    processor = PdfProcessor()
    result = processor.process(sample_valid_pdf, output_path=output_pdf)

    assert result["success"] is True
    assert result["pages"] == 28
    assert result["size_bytes"] == len(sample_valid_pdf)
    assert output_pdf.exists()
    assert output_pdf.stat().st_size == len(sample_valid_pdf)


def test_full_pipeline_repairs_and_validates_obfuscated_pdf(sample_obfuscated_pdf, sample_valid_pdf, tmp_path):
    """
    Test that the pipeline takes an obfuscated Wuolah file (which lacks valid %PDF signature),
    analyzes it, passes it through the normalizer hook which fixes the 128 bytes XOR 27,
    and then successfully validates and writes the clean 28-page PDF.
    """
    output_pdf = tmp_path / "repaired_wuolah.pdf"
    processor = PdfProcessor(normalizer=DefaultNormalizer())

    # Ensure pre-condition: raw data lacks %PDF header
    assert not sample_obfuscated_pdf.startswith(b"%PDF")

    result = processor.process(sample_obfuscated_pdf, output_path=output_pdf)

    assert result["success"] is True
    assert result["pages"] == 28
    assert result["detected_type"] == "wuolah_xor_obfuscated"
    assert result["data"] == sample_valid_pdf
    assert output_pdf.exists()
    assert output_pdf.read_bytes() == sample_valid_pdf


def test_pipeline_fails_on_obfuscated_file_if_passthrough_normalizer_used(sample_obfuscated_pdf, tmp_path):
    """
    Shows that if a normalizer does NOT handle the transformation (like PassthroughNormalizer),
    the validator catches the invalid PDF and raises InvalidPdfError.
    """
    output_pdf = tmp_path / "failed.pdf"
    processor = PdfProcessor(normalizer=PassthroughNormalizer())

    with pytest.raises(InvalidPdfError) as exc_info:
        processor.process(sample_obfuscated_pdf, output_path=output_pdf)

    assert "no se puede abrir el documento como pdf" in str(exc_info.value).lower()
    assert not output_pdf.exists()


def test_pipeline_fails_on_corrupt_data(sample_corrupted_pdf, tmp_path):
    output_pdf = tmp_path / "corrupt.pdf"
    processor = PdfProcessor()

    with pytest.raises(InvalidPdfError):
        processor.process(sample_corrupted_pdf, output_path=output_pdf)


def test_pipeline_fails_on_html(sample_html, tmp_path):
    output_pdf = tmp_path / "html.pdf"
    processor = PdfProcessor()

    with pytest.raises(InvalidPdfError):
        processor.process(sample_html, output_path=output_pdf)

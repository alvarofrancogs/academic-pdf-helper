from backend.pdf.analyzer import PdfAnalyzer


def test_analyze_valid_pdf(sample_valid_pdf):
    analysis = PdfAnalyzer.analyze(sample_valid_pdf, content_type="application/pdf")
    assert analysis["analysis_ok"] is True
    assert analysis["starts_with_pdf_signature"] is True
    assert analysis["detected_type"] == "pdf"
    assert analysis["size_bytes"] == len(sample_valid_pdf)
    assert len(analysis["header_sample"]) > 0


def test_analyze_empty_file():
    analysis = PdfAnalyzer.analyze(b"")
    assert analysis["analysis_ok"] is False
    assert analysis["starts_with_pdf_signature"] is False
    assert analysis["detected_type"] == "empty"
    assert analysis["size_bytes"] == 0


def test_analyze_obfuscated_wuolah_pdf(sample_obfuscated_pdf):
    analysis = PdfAnalyzer.analyze(sample_obfuscated_pdf, content_type="application/octet-stream")
    assert analysis["analysis_ok"] is True
    assert analysis["starts_with_pdf_signature"] is False
    assert analysis["detected_type"] == "wuolah_xor_obfuscated"
    assert analysis["size_bytes"] == len(sample_obfuscated_pdf)


def test_analyze_html_response(sample_html):
    analysis = PdfAnalyzer.analyze(sample_html, content_type="text/html")
    assert analysis["analysis_ok"] is True
    assert analysis["starts_with_pdf_signature"] is False
    assert analysis["detected_type"] == "html"


def test_analyze_json_response(sample_json):
    analysis = PdfAnalyzer.analyze(sample_json, content_type="application/json")
    assert analysis["analysis_ok"] is True
    assert analysis["starts_with_pdf_signature"] is False
    assert analysis["detected_type"] == "json"

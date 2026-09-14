from backend.pdf.default_normalizer import DefaultNormalizer, PassthroughNormalizer
from backend.pdf.normalizer import PdfNormalizer


def test_normalizer_protocol_compliance():
    default_norm = DefaultNormalizer()
    passthrough_norm = PassthroughNormalizer()

    assert isinstance(default_norm, PdfNormalizer)
    assert isinstance(passthrough_norm, PdfNormalizer)


def test_default_normalizer_leaves_valid_pdf_untouched(sample_valid_pdf):
    normalizer = DefaultNormalizer()
    result = normalizer.normalize(sample_valid_pdf)
    assert result == sample_valid_pdf


def test_default_normalizer_repairs_wuolah_xor_obfuscation(sample_valid_pdf, sample_obfuscated_pdf):
    normalizer = DefaultNormalizer()
    
    # Precondition: the obfuscated version does not start with %PDF
    assert not sample_obfuscated_pdf.startswith(b"%PDF")

    # Act
    repaired_pdf = normalizer.normalize(sample_obfuscated_pdf)

    # Assert: repaired PDF starts with %PDF and matches the uncorrupted stream
    assert repaired_pdf.startswith(b"%PDF")
    assert repaired_pdf == sample_valid_pdf


def test_normalizer_empty_and_short_data():
    normalizer = DefaultNormalizer()
    assert normalizer.normalize(b"") == b""
    assert normalizer.normalize(b"short") == b"short"


def test_default_normalizer_removes_wuolah_cover_page():
    import pymupdf
    normalizer = DefaultNormalizer()

    # Create a 2-page mock document where page 1 is a Wuolah cover template
    doc = pymupdf.open()
    
    # Page 1: Wuolah cover
    p1 = doc.new_page()
    p1.insert_text((50, 100), "Apuntes Wuolah - Accede al documento original")
    p1.insert_text((50, 200), "Reservados todos los derechos")
    
    # Page 2: Student notes
    p2 = doc.new_page()
    p2.insert_text((50, 100), "Apuntes reales del alumno - Tema 1 Algoritmos")
    
    raw_bytes = doc.tobytes()
    doc.close()

    cleaned_bytes = normalizer.normalize(raw_bytes)
    cleaned_doc = pymupdf.open(stream=cleaned_bytes, filetype="pdf")

    # Verify cover was removed and only student notes remain
    assert len(cleaned_doc) == 1
    page_text = cleaned_doc[0].get_text()
    assert "Apuntes reales del alumno" in page_text
    assert "Accede al documento original" not in page_text
    cleaned_doc.close()


def test_default_normalizer_cleans_watermarks():
    import pymupdf
    normalizer = DefaultNormalizer()

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 100), "wuolah: Contenido legitimo del estudiante")
    page.insert_text((50, 800), "Reservados todos los derechos. No se permite la explotación económica.")
    
    raw_bytes = doc.tobytes()
    doc.close()

    cleaned_bytes = normalizer.normalize(raw_bytes)
    cleaned_doc = pymupdf.open(stream=cleaned_bytes, filetype="pdf")

    text = cleaned_doc[0].get_text()
    assert "Contenido legitimo del estudiante" in text
    assert "Reservados todos los derechos" not in text
    cleaned_doc.close()


def test_default_normalizer_cleans_preview_watermark_overlay():
    import pymupdf
    normalizer = DefaultNormalizer()

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 100), "Apuntes originales de Matemáticas Discretas")
    page.insert_text((250, 360), "Vista previa del documento.\nMostrando 4 páginas de 8")

    raw_bytes = doc.tobytes()
    doc.close()

    cleaned_bytes = normalizer.normalize(raw_bytes)
    cleaned_doc = pymupdf.open(stream=cleaned_bytes, filetype="pdf")

    text = cleaned_doc[0].get_text()
    assert "Apuntes originales de Matemáticas Discretas" in text
    assert "Vista previa" not in text
    assert "Mostrando" not in text
    cleaned_doc.close()


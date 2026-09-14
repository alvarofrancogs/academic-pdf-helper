import io
import pytest
import pypdf

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None


@pytest.fixture(scope="session")
def sample_valid_pdf() -> bytes:
    """Generate a clean 28-page valid PDF test document."""
    if fitz is not None:
        doc = fitz.open()
        for i in range(28):
            page = doc.new_page()
            page.insert_text((72, 72), f"Wuolah PDF Helper Test Document - Página {i+1}")
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes
    else:
        writer = pypdf.PdfWriter()
        for _ in range(28):
            writer.add_blank_page(width=612, height=792)
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()


@pytest.fixture(scope="session")
def sample_single_page_pdf() -> bytes:
    """Generate a 1-page valid PDF test document."""
    if fitz is not None:
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Página 1 de prueba")
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes
    else:
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=612, height=792)
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()


@pytest.fixture(scope="session")
def sample_obfuscated_pdf(sample_valid_pdf: bytes) -> bytes:
    """
    Generate an XOR-27 poisoned document mimicking Wuolah's anti-scraping
    transformation where the first 128 bytes are XORed with 0x1B (27).
    """
    assert len(sample_valid_pdf) >= 128
    return bytes([b ^ 27 for b in sample_valid_pdf[:128]]) + sample_valid_pdf[128:]


@pytest.fixture(scope="session")
def sample_corrupted_pdf() -> bytes:
    """Return corrupted non-valid PDF bytes starting with %PDF but unparseable."""
    return b"%PDF-1.7\nCorrupted binary content that cannot be parsed as valid PDF structure..."


@pytest.fixture(scope="session")
def sample_html() -> bytes:
    """Sample HTML response returned by error pages."""
    return b"<!DOCTYPE html><html><head><title>403 Forbidden</title></head><body>Acceso denegado</body></html>"


@pytest.fixture(scope="session")
def sample_json() -> bytes:
    """Sample JSON response returned by error APIs."""
    return b'{"error": "Unauthorized", "message": "Inicia sesion para continuar"}'

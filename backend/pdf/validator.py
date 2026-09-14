import io
import re
from typing import Any, Dict
from backend.core.config import settings

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

import pypdf


class PdfValidationError(Exception):
    """Raised when PDF validation fails."""
    pass


class PdfValidator:
    """Validates PDF documents using PyMuPDF and pypdf."""

    PDF_MAGIC = b"%PDF"

    @classmethod
    def validate(cls, data: bytes) -> Dict[str, Any]:
        size_bytes = len(data)

        if size_bytes == 0:
            return {
                "valid": False,
                "pages": 0,
                "size_bytes": 0,
                "error": "El archivo recibido está vacío.",
            }

        # Size check
        if size_bytes > settings.max_pdf_size_bytes:
            return {
                "valid": False,
                "pages": 0,
                "size_bytes": size_bytes,
                "error": f"El archivo excede el tamaño máximo permitido ({settings.MAX_PDF_SIZE_MB} MB).",
            }

        # Header magic check
        if not data.startswith(cls.PDF_MAGIC):
            return {
                "valid": False,
                "pages": 0,
                "size_bytes": size_bytes,
                "error": "No se puede abrir el documento como PDF (firma de cabecera inválida).",
            }

        # Extract version from header (e.g., %PDF-1.7)
        pdf_version = "1.7"
        header_match = re.match(rb"%PDF-(\d+\.\d+)", data[:20])
        if header_match:
            pdf_version = header_match.group(1).decode("latin1", errors="ignore")

        # PyMuPDF validation
        pages_count = 0
        opened_successfully = False

        if fitz is not None:
            try:
                doc = fitz.open(stream=data, filetype="pdf")
                if doc.is_encrypted:
                    # Try decrypting with empty password if just read permissions
                    try:
                        doc.authenticate("")
                    except Exception:
                        pass
                pages_count = doc.page_count
                if pages_count > 0:
                    # Test rendering / loading first page to ensure integrity
                    _ = doc[0].rect
                doc.close()
                opened_successfully = True
            except Exception as e:
                # Log or fall back to pypdf check
                pass

        # Fallback or secondary check with pypdf
        if not opened_successfully or pages_count == 0:
            try:
                reader = pypdf.PdfReader(io.BytesIO(data))
                if reader.is_encrypted:
                    try:
                        reader.decrypt("")
                    except Exception:
                        pass
                pages_count = len(reader.pages)
                if pages_count > 0:
                    _ = reader.pages[0]  # Verify page access
                opened_successfully = True
            except Exception as e:
                return {
                    "valid": False,
                    "pages": 0,
                    "size_bytes": size_bytes,
                    "error": f"No se puede abrir el documento como PDF: {str(e)}",
                }

        if not opened_successfully or pages_count <= 0:
            return {
                "valid": False,
                "pages": 0,
                "size_bytes": size_bytes,
                "error": "El documento no contiene páginas válidas o está dañado.",
            }

        return {
            "valid": True,
            "pages": pages_count,
            "size_bytes": size_bytes,
            "pdf_version": pdf_version,
        }

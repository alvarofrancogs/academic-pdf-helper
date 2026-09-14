from typing import Any, Dict


class PdfAnalyzer:
    """Analyzes raw bytes before attempting to parse as a PDF document."""

    PDF_MAGIC = b"%PDF"
    XOR_KEY = 27  # 0x1B

    @classmethod
    def analyze(cls, data: bytes, content_type: str | None = None) -> Dict[str, Any]:
        size_bytes = len(data)
        if size_bytes == 0:
            return {
                "size_bytes": 0,
                "starts_with_pdf_signature": False,
                "detected_type": "empty",
                "header_sample": "",
                "analysis_ok": False,
                "error": "El archivo recibido está vacío.",
            }

        # Safe header sample (first 16 bytes in hex)
        sample_len = min(16, size_bytes)
        header_sample = data[:sample_len].hex(" ")

        starts_with_pdf = data.startswith(cls.PDF_MAGIC)

        # Detect types
        detected_type = "unknown"
        if starts_with_pdf:
            detected_type = "pdf"
        elif size_bytes >= 4 and bytes([b ^ cls.XOR_KEY for b in data[:4]]) == cls.PDF_MAGIC:
            detected_type = "wuolah_xor_obfuscated"
        else:
            # Check for HTML or JSON error responses
            stripped_start = data[:512].strip()
            if stripped_start.startswith((b"<!DOCTYPE html", b"<html", b"<HTML")):
                detected_type = "html"
            elif stripped_start.startswith((b"{", b"[")):
                detected_type = "json"

        return {
            "size_bytes": size_bytes,
            "starts_with_pdf_signature": starts_with_pdf,
            "detected_type": detected_type,
            "header_sample": header_sample,
            "analysis_ok": True,
            "content_type": content_type,
        }

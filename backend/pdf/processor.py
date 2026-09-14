from pathlib import Path
from typing import Any, Dict, Optional
from backend.pdf.analyzer import PdfAnalyzer
from backend.pdf.default_normalizer import DefaultNormalizer
from backend.pdf.normalizer import PdfNormalizer
from backend.pdf.validator import PdfValidator, PdfValidationError


class InvalidPdfError(PdfValidationError):
    """Raised when document cannot be processed or validated as a valid PDF."""
    pass


class PdfProcessor:
    """
    Orchestrates the PDF processing pipeline:
    RAW BYTES -> Analyzer -> Normalizer -> Validator -> Processor -> FINAL PDF
    """

    def __init__(self, normalizer: Optional[PdfNormalizer] = None):
        self.normalizer: PdfNormalizer = normalizer if normalizer is not None else DefaultNormalizer()

    def process(
        self,
        raw_data: bytes,
        output_path: Optional[Path] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full pipeline on raw data bytes.
        """
        # 1. Analyze raw bytes
        analysis = PdfAnalyzer.analyze(raw_data, content_type=content_type)
        if not analysis["analysis_ok"]:
            raise InvalidPdfError(analysis.get("error", "Error analizando los bytes del documento."))

        # 2. Normalize bytes (e.g. deobfuscate XOR-27 Wuolah header if needed)
        normalized_data = self.normalizer.normalize(raw_data)

        # 3. Validate normalized PDF bytes
        validation = PdfValidator.validate(normalized_data)
        if not validation["valid"]:
            error_msg = validation.get("error", "El archivo no es un PDF válido.")
            raise InvalidPdfError(error_msg)

        # 4. Save to destination if output_path is provided
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(normalized_data)

        # 5. Format human-readable size
        size_bytes = validation["size_bytes"]
        if size_bytes >= 1024 * 1024:
            size_formatted = f"{size_bytes / (1024 * 1024):.2f} MB".replace(".", ",")
        elif size_bytes >= 1024:
            size_formatted = f"{size_bytes / 1024:.2f} KB".replace(".", ",")
        else:
            size_formatted = f"{size_bytes} B"

        return {
            "success": True,
            "pages": validation["pages"],
            "size_bytes": size_bytes,
            "size_formatted": size_formatted,
            "pdf_version": validation.get("pdf_version", "1.7"),
            "detected_type": analysis.get("detected_type"),
            "data": normalized_data,
            "output_path": str(output_path) if output_path else None,
        }

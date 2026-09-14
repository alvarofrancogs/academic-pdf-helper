import logging
import pymupdf

logger = logging.getLogger("wuolah.normalizer")


class DefaultNormalizer:
    """
    Default document byte normalizer implementing PdfNormalizer.
    
    1. Checks and repairs Wuolah's 128-byte XOR-27 obfuscation if present.
    2. Cleans Wuolah cover pages (Page 1) and margin watermarks
       ('Reservados todos los derechos...') using PyMuPDF.
    """

    PDF_MAGIC = b"%PDF"
    XOR_KEY = 27  # 0x1B
    OBFUSCATION_HEADER_LENGTH = 128

    WATERMARK_PHRASES = [
        "Reservados todos los derechos",
        "No se permite la explotación económica",
        "Queda permitida la impresión en su totalidad",
    ]

    def normalize(self, data: bytes) -> bytes:
        if not data:
            return data

        # Step 1: Wuolah anti-scraping XOR de-obfuscation:
        # Wuolah obfuscates the first 128 bytes with XOR key 27 (0x1B).
        # We test if the first 4 bytes XORed with 27 match '%PDF'.
        if not data.startswith(self.PDF_MAGIC):
            if len(data) >= self.OBFUSCATION_HEADER_LENGTH:
                test_magic = bytes([b ^ self.XOR_KEY for b in data[:4]])
                if test_magic == self.PDF_MAGIC:
                    deobfuscated_header = bytes([b ^ self.XOR_KEY for b in data[:self.OBFUSCATION_HEADER_LENGTH]])
                    data = deobfuscated_header + data[self.OBFUSCATION_HEADER_LENGTH:]

        # If data still does not start with %PDF, return as-is for downstream validation
        if not data.startswith(self.PDF_MAGIC):
            return data

        # Step 2: Clean Wuolah cover page and watermarks
        try:
            doc = pymupdf.open(stream=data, filetype="pdf")
            if len(doc) == 0:
                return data

            modified = False

            # 2a. Detect and delete Wuolah cover page (Page 1)
            if len(doc) > 1:
                p1_text = doc[0].get_text().lower()
                is_cover = (
                    "accede al documento original" in p1_text or
                    ("wuolah" in p1_text and "reservados todos los derechos" in p1_text)
                )
                if is_cover:
                    logger.info("Detectada portada de Wuolah en página 1 -> Eliminándola del PDF final.")
                    doc.delete_page(0)
                    modified = True

            # 2b. Clean watermark phrases from margins of remaining pages
            for page in doc:
                found_watermark = False
                for phrase in self.WATERMARK_PHRASES:
                    matches = page.search_for(phrase)
                    if matches:
                        found_watermark = True
                        for rect in matches:
                            # Add slight padding to completely erase the text line cleanly
                            padded = pymupdf.Rect(rect.x0 - 2, rect.y0 - 2, rect.x1 + 2, rect.y1 + 2)
                            page.add_redact_annot(padded, fill=(1, 1, 1))
                if found_watermark:
                    page.apply_redactions()
                    modified = True

            # 2c. Clean Wuolah 'Vista previa del documento / Mostrando X páginas' overlay card
            has_any_preview_wm = any(
                any(k in page.get_text().lower() for k in ["vista previa", "mostrando"])
                for page in doc
            )
            if has_any_preview_wm:
                logger.info("Detectadas marcas de agua 'Vista previa del documento' -> Procediendo a extirparlas.")
                clean_doc = pymupdf.open()
                for i, page in enumerate(doc):
                    text = page.get_text()
                    has_preview_wm = any(k in text.lower() for k in ["vista previa", "mostrando"])
                    imgs = page.get_images()

                    is_scanned = False
                    bg_data = None
                    if has_preview_wm and len(imgs) >= 2:
                        max_dim = 0
                        for img_info in imgs:
                            base = doc.extract_image(img_info[0])
                            dim = base["width"] * base["height"]
                            if dim > max_dim:
                                max_dim = dim
                                bg_data = base["image"]
                        if max_dim > 1500 * 1500:
                            is_scanned = True

                    if is_scanned and bg_data:
                        # Scanned notes: preserve the clean full-res handwritten background image
                        rect = page.rect
                        new_page = clean_doc.new_page(width=rect.width, height=rect.height)
                        new_page.insert_image(rect, stream=bg_data)
                        modified = True
                    else:
                        # Digital text document: delete watermark card image and remove text layer without color fill
                        if has_preview_wm:
                            for img_info in imgs:
                                base = doc.extract_image(img_info[0])
                                if (base["width"], base["height"]) == (657, 239) or (base["width"] < 1000 and base["height"] < 500):
                                    page.delete_image(img_info[0])
                                    modified = True

                            for phrase in ["Vista previa", "del documento", "del", "documento", "Mostrando", "páginas de", "paginas de"]:
                                for rect in page.search_for(phrase):
                                    page.add_redact_annot(rect, fill=None)
                            page.apply_redactions(images=0)
                            modified = True

                        clean_doc.insert_pdf(doc, from_page=i, to_page=i)

                doc.close()
                doc = clean_doc

            if modified:
                cleaned_bytes = doc.tobytes(garbage=4, deflate=True)
                doc.close()
                return cleaned_bytes

            doc.close()
            return data
        except Exception as e:
            logger.warning(f"No se pudo completar la limpieza avanzada del PDF con PyMuPDF: {e}. Entregando versión desofuscada base.")
            return data


class PassthroughNormalizer:
    """A pure passthrough normalizer for baseline testing."""

    def normalize(self, data: bytes) -> bytes:
        return data

import pymupdf

def clean_wuolah_pdf(pdf_bytes: bytes) -> bytes:
    """
    Remove Wuolah cover page, advertisement pages, and margin watermarks
    from a valid PDF document stream.
    """
    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
        return pdf_bytes

    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        if len(doc) == 0:
            return pdf_bytes

        # 1. Detect and remove Wuolah cover page (Page 1)
        if len(doc) > 1:
            p1_text = doc[0].get_text().lower()
            is_cover = (
                "accede al documento original" in p1_text or
                ("wuolah" in p1_text and "reservados todos los derechos" in p1_text)
            )
            if is_cover:
                doc.delete_page(0)

        # 2. Detect and remove any full-page ads (if any were inserted)
        pages_to_delete = []
        for idx, page in enumerate(doc):
            text = page.get_text().lower()
            # If the entire page is an ad with little or no user content
            if "plan turbo" in text or "hazte pro" in text or "eliminar anuncios" in text:
                images = page.get_images()
                # If page only has ad images and ad text
                if len(text) < 400 and len(images) <= 2:
                    pages_to_delete.append(idx)
                    
        for idx in reversed(pages_to_delete):
            if len(doc) > 1:
                doc.delete_page(idx)

        # 3. Clean margin watermarks on remaining pages
        watermark_phrases = [
            "Reservados todos los derechos",
            "No se permite la explotación económica",
            "Queda permitida la impresión en su totalidad",
        ]
        
        for page in doc:
            for phrase in watermark_phrases:
                for rect in page.search_for(phrase):
                    # Redact watermark text cleanly with white background
                    padded = pymupdf.Rect(rect.x0 - 2, rect.y0 - 2, rect.x1 + 2, rect.y1 + 2)
                    page.add_redact_annot(padded, fill=(1, 1, 1))
            page.apply_redactions()

        cleaned_bytes = doc.tobytes(garbage=4, deflate=True)
        doc.close()
        return cleaned_bytes
    except Exception as e:
        print(f"Error cleaning PDF: {e}")
        return pdf_bytes

# Test with the raw 9-page PDF
import tempfile
from pathlib import Path

temp_pdf = Path(tempfile.gettempdir()) / "wuolah-pdf" / "ef864d1234d4" / "wuolah-free-Apuntes-parcial2.pdf"
if temp_pdf.exists():
    with open(temp_pdf, "rb") as f:
        data = f.read()
else:
    data = b"%PDF-1.4 mock content"

raw = data
cleaned = clean_wuolah_pdf(raw)
print(f"Original size: {len(raw)} bytes -> Cleaned size: {len(cleaned)} bytes")
test_doc = pymupdf.open(stream=cleaned, filetype="pdf")
print(f"Páginas resultantes: {len(test_doc)}")
for i in range(len(test_doc)):
    print(f"Página {i+1}: {repr(test_doc[i].get_text()[:60])}")

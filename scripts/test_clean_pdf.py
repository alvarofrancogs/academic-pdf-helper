import fitz
from pathlib import Path

# Load the PDF from test_no_ads
pdf_path = Path("artifacts/inspeccion_paginas") # or test_no_ads
# Let's test on the newly downloaded 9-page PDF
import tempfile

temp_dir = Path(tempfile.gettempdir()) / "wuolah-pdf"
latest_pdf = max(temp_dir.glob("*/*.pdf"), key=lambda p: p.stat().st_mtime)
print(f"Abriendo: {latest_pdf}")

doc = fitz.open(latest_pdf)
print(f"Páginas antes: {len(doc)}")

# 1. Check if Page 1 is a Wuolah generated cover
p1_text = doc[0].get_text().lower()
is_wuolah_cover = any(w in p1_text for w in ["accede al documento original", "wuolah", "reservados todos los derechos"]) and any(w in p1_text for w in ["grado en", "universidad", "facultad", "escuela de"])
print(f"¿Página 1 es portada de Wuolah?: {is_wuolah_cover}")

if is_wuolah_cover:
    print("Eliminando portada de Wuolah (página 1)...")
    doc.delete_page(0)

print(f"Páginas tras quitar portada: {len(doc)}")

# 2. Check remaining pages for watermarks:
# "Reservados todos los derechos..."
# In PyMuPDF, we can find text and redact it, or remove blocks!
watermark_phrases = [
    "Reservados todos los derechos",
    "No se permite la explotación económica",
    "Queda permitida la impresión en su totalidad",
]

for idx, page in enumerate(doc):
    for phrase in watermark_phrases:
        text_instances = page.search_for(phrase)
        for inst in text_instances:
            # We can redact it cleanly (erase the watermark text)
            page.add_redact_annot(inst, fill=(1, 1, 1)) # white fill
            
    # Also search for the upload hash in margin, e.g. at top y < 30 or bottom y > 820
    blocks = page.get_text("blocks")
    for b in blocks:
        # Check if block is at bottom margin (y > 815) or top margin (y < 25)
        bbox = b[:4]
        b_text = b[4].strip()
        if (bbox[1] > 815 or bbox[3] < 20) and any(w in b_text.lower() for w in ["reservados", "derechos", "explotación", "wuolah"]) or ("-" in b_text and len(b_text) > 25 and bbox[3] < 15):
            rect = fitz.Rect(bbox)
            page.add_redact_annot(rect, fill=(1, 1, 1))
            
    page.apply_redactions()

out_clean_path = Path("artifacts/pdf_completamente_limpio.pdf")
doc.save(str(out_clean_path))
print(f"¡PDF limpio guardado en: {out_clean_path} ({out_clean_path.stat().st_size} bytes, {len(doc)} páginas)!")

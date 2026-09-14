import fitz
from pathlib import Path

import tempfile
temp_dir = Path(tempfile.gettempdir()) / "wuolah-pdf"
pdf_files = list(temp_dir.glob("*/*.pdf"))
if not pdf_files:
    print("No PDFs found")
    exit(0)
pdf_path = pdf_files[0]
doc = fitz.open(pdf_path)

out_dir = Path("artifacts/inspeccion_paginas")
out_dir.mkdir(parents=True, exist_ok=True)

# Render pages as pixmaps to see them clearly
for i in range(min(5, len(doc))):
    page = doc[i]
    pix = page.get_pixmap(dpi=100)
    pix.save(str(out_dir / f"pagina_{i+1}.png"))
    print(f"Página {i+1} guardada: {out_dir / f'pagina_{i+1}.png'}")

# Also inspect text on each page
for i in range(min(5, len(doc))):
    page = doc[i]
    print(f"\n--- PÁGINA {i+1} ---")
    for b in page.get_text("blocks"):
        print(f"  bbox={b[:4]}: {b[4].strip()[:80]}")

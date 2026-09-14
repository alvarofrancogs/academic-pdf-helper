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

out_dir = Path("artifacts/inspeccion_imagenes")
out_dir.mkdir(parents=True, exist_ok=True)

for xref in [55, 71, 45, 5, 40, 53, 54, 47, 48, 11]:
    try:
        img = doc.extract_image(xref)
        ext = img["ext"]
        img_bytes = img["image"]
        out_file = out_dir / f"img_{xref}.{ext}"
        with open(out_file, "wb") as f:
            f.write(img_bytes)
        print(f"xref {xref}: {out_file} ({len(img_bytes)} bytes, {img['width']}x{img['height']})")
    except Exception as e:
        print(f"Error xref {xref}: {e}")

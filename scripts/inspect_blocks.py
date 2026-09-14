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

print(f"Total páginas: {len(doc)}")

for page_idx, page in enumerate(doc):
    print(f"\n==================== PÁGINA {page_idx + 1} ====================")
    blocks = page.get_text("blocks")
    for b_idx, b in enumerate(blocks):
        # b is (x0, y0, x1, y1, text, block_no, block_type)
        bbox = (round(b[0], 1), round(b[1], 1), round(b[2], 1), round(b[3], 1))
        text = b[4].replace("\n", " ").strip()
        if text:
            print(f"  Bloque {b_idx} [bbox={bbox}]: '{text}'")
            
    images = page.get_images()
    print(f"  Imágenes: {len(images)}")
    for img in images:
        xref = img[0]
        base_img = doc.extract_image(xref)
        print(f"    Img xref={xref}, formato={base_img.get('ext')}, dimensiones={base_img.get('width')}x{base_img.get('height')}")

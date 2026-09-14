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

for idx, page in enumerate(doc):
    images = page.get_images()
    text = page.get_text()
    
    # Check if this page has the main document image
    main_doc_imgs = [img for img in images if doc.extract_image(img[0]).get("width", 0) > 1000]
    print(f"Página {idx+1}: {len(images)} imágenes en total, {len(main_doc_imgs)} imagen(es) grande (>1000px ancho)")
    for img in main_doc_imgs:
        info = doc.extract_image(img[0])
        print(f"   -> xref {img[0]}: {info.get('width')}x{info.get('height')}")

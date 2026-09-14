import fitz  # PyMuPDF
from pathlib import Path

# Find the last downloaded PDF
import tempfile

temp_dir = Path(tempfile.gettempdir()) / "wuolah-pdf"
pdf_files = list(temp_dir.glob("*/*.pdf"))
if not pdf_files:
    print("No PDFs found in temp dir.")
    exit(1)

latest_pdf = max(pdf_files, key=lambda p: p.stat().st_mtime)
print(f"Analizando: {latest_pdf} ({latest_pdf.stat().st_size} bytes)")

doc = fitz.open(latest_pdf)
print(f"Total páginas: {len(doc)}")

for page_idx in range(len(doc)):
    page = doc[page_idx]
    text = page.get_text().strip()
    images = page.get_images()
    print(f"\n--- PÁGINA {page_idx + 1} (Rect: {page.rect}, {len(images)} imágenes) ---")
    lines = text.split("\n")
    preview = " | ".join([line.strip() for line in lines[:8] if line.strip()])
    print(f"Texto ({len(text)} caracteres): {preview[:200]}")
    
    # Check if this page is an ad
    lower_text = text.lower()
    is_ad = any(k in lower_text for k in [
        "patrocinado", "wuolah", "descarga", "publicidad", "anuncio", 
        "aprueba", "hazte pro", "sin publi", "código de descuento", "promo"
    ])
    print(f"¿Contiene palabras de anuncio/Wuolah?: {is_ad}")

import asyncio
import json
import sys
from pathlib import Path
import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from backend.core.config import settings

async def generate_perfect_clean_pdf():
    profile_dir = settings.temp_path / "browser_profile"
    
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(user_data_dir=str(profile_dir), headless=True)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://wuolah.com", wait_until="domcontentloaded")
        
        cookies = await ctx.cookies("https://wuolah.com")
        token_cookie = next((c["value"] for c in cookies if c["name"] == "token"), None)
        headers = {
            "Authorization": f"Bearer {token_cookie}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        doc_id = 14074552
        print(f"1. Solicitando descarga sin anuncios para doc_id={doc_id}...")
        resp = await page.request.post(
            "https://api.wuolah.com/v2/download",
            data=json.dumps({
                "fileId": doc_id,
                "noAdsWithCoins": False,
                "avoidFallback": True,
                "adblockDetected": False
            }),
            headers=headers
        )
        data = await resp.json()
        pdf_url = data.get("url")
        print(f"   URL: {pdf_url[:70]}...")
        
        pdf_resp = await page.request.get(pdf_url)
        pdf_bytes = await pdf_resp.body()
        print(f"2. Descargados {len(pdf_bytes)} bytes. Abriendo con PyMuPDF...")
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        print(f"   Páginas iniciales: {len(doc)}")
        
        # Check cover page
        p1 = doc[0].get_text().lower()
        if "accede al documento original" in p1 or ("wuolah" in p1 and "reservados todos los derechos" in p1):
            print("3. Detectada portada de Wuolah en página 1 -> Eliminándola...")
            doc.delete_page(0)
            
        print(f"   Páginas de apuntes reales: {len(doc)}")
        
        # Remove watermarks
        for page_obj in doc:
            for phrase in ["Reservados todos los derechos", "No se permite la explotación económica", "Queda permitida la impresión en su totalidad"]:
                matches = page_obj.search_for(phrase)
                for rect in matches:
                    # expand rect slightly to erase completely
                    padded_rect = fitz.Rect(rect.x0 - 2, rect.y0 - 2, rect.x1 + 2, rect.y1 + 2)
                    page_obj.add_redact_annot(padded_rect, fill=(1, 1, 1))
            page_obj.apply_redactions()
            
        out_file = Path("artifacts/apuntes_100_limpios.pdf")
        doc.save(str(out_file), garbage=4, deflate=True)
        print(f"4. ¡DOCUMENTO FINAL GUARDADO EN {out_file}!")
        print(f"   Páginas: {len(doc)}, Tamaño: {out_file.stat().st_size} bytes")
        
        # Verify text on all pages
        for i in range(len(doc)):
            txt = doc[i].get_text().strip()
            print(f"   Pág {i+1}: {repr(txt[:60])}")

        await ctx.close()

if __name__ == "__main__":
    asyncio.run(generate_perfect_clean_pdf())

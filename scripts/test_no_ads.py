import asyncio
import json
import sys
from pathlib import Path
import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from backend.core.config import settings

async def test_rendered_ads_zero():
    profile_dir = settings.temp_path / "browser_profile"
    
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://wuolah.com", wait_until="domcontentloaded")
        
        cookies = await ctx.cookies("https://wuolah.com")
        token_cookie = next((c["value"] for c in cookies if c["name"] == "token"), None)
        headers = {
            "Authorization": f"Bearer {token_cookie}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Test with the 10-page document from the user: 14074552
        doc_id = 14074552
        print(f"Probando 'avoidFallback': True en documento {doc_id}...")
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
        print("Status:", resp.status)
        data = await resp.json()
        print("renderedAds devueltos:", len(data.get("renderedAds", [])))
        pdf_url = data.get("url")
        print("URL:", pdf_url[:80])
        
        pdf_resp = await page.request.get(pdf_url)
        pdf_bytes = await pdf_resp.body()
        print(f"Bytes descargados: {len(pdf_bytes)}")
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        print(f"Total páginas en el PDF: {len(doc)}")
        for i in range(len(doc)):
            txt = doc[i].get_text().strip().replace("\n", " ")
            has_ad = "turbo" in txt.lower() or "publicidad" in txt.lower() or "anuncio" in txt.lower()
            print(f"  Página {i+1}: {len(txt)} chars | ¿Anuncio en texto?: {has_ad} | Preview: '{txt[:70]}'")

        await ctx.close()

if __name__ == "__main__":
    asyncio.run(test_rendered_ads_zero())

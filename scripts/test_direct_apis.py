import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from backend.core.config import settings

async def test_apis():
    profile_dir = settings.temp_path / "browser_profile"
    
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://wuolah.com", wait_until="domcontentloaded")
        
        # 1. Fetch document metadata directly
        doc_resp = await page.request.get("https://api.wuolah.com/v2/documents/14080870")
        doc_json = await doc_resp.json()
        print("=== DOCUMENT METADATA (14080870) ===")
        print("fileUrl:", doc_json.get("fileUrl"))
        print("uploadId:", doc_json.get("uploadId"))
        print("requiredAds:", doc_json.get("requiredAds"))
        print("size:", doc_json.get("size"))
        
        # 2. Test fetching fileUrl if it exists
        file_url = doc_json.get("fileUrl")
        if file_url:
            print(f"\nProbando GET directo a fileUrl: {file_url[:80]}...")
            resp = await page.request.get(file_url)
            print("Status de fileUrl:", resp.status)
            print("Content-Type de fileUrl:", resp.headers.get("content-type"))
            body = await resp.body()
            print("Bytes recibidos de fileUrl:", len(body))
            if len(body) >= 4:
                print("Magic bytes:", body[:4])
                xor_magic = bytes([b ^ 27 for b in body[:4]])
                print("XOR 27 magic:", xor_magic)
        
        # 3. Test calling POST /v2/download IMMEDIATELY without waiting 50s!
        print("\n=== PROBANDO POST /v2/download DIRECTO (SIN ESPERAR ANUNCIO) ===")
        # We test with a minimal payload
        minimal_payload = {
            "fileId": 14080870,
            "adblockDetected": False,
            "noAdsWithCoins": False,
            "avoidFallback": False
        }
        
        dl_resp = await page.request.post(
            "https://api.wuolah.com/v2/download",
            data=json.dumps(minimal_payload),
            headers={"Content-Type": "application/json", "Accept": "application/json"}
        )
        print("Status de POST /v2/download (minimal payload):", dl_resp.status)
        try:
            dl_json = await dl_resp.json()
            print("JSON de POST /v2/download:")
            print("downloadId:", dl_json.get("downloadId"))
            print("url:", dl_json.get("url"))
            print("isEncrypted:", dl_json.get("isEncrypted"))
            print("extension:", dl_json.get("extension"))
            
            # If URL returned, test fetching it!
            if dl_json.get("url"):
                pdf_resp = await page.request.get(dl_json["url"])
                print(f"Status de descarga del PDF ({dl_json['url'][:60]}...):", pdf_resp.status)
                print("Content-Type:", pdf_resp.headers.get("content-type"))
                pdf_bytes = await pdf_resp.body()
                print("Bytes de PDF recibidos:", len(pdf_bytes))
                print("Comienza con %PDF:", pdf_bytes.startswith(b"%PDF"))
        except Exception as e:
            text = await dl_resp.text()
            print(f"Error parseando JSON o error devuelto: {e}")
            print("Respuesta texto:", text[:300])

        await ctx.close()

if __name__ == "__main__":
    asyncio.run(test_apis())

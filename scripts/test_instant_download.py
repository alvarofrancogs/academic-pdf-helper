import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from backend.core.config import settings
from backend.pdf.analyzer import PdfAnalyzer
from backend.pdf.default_normalizer import DefaultNormalizer
from backend.pdf.validator import PdfValidator

async def test_full_pipeline_direct():
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
        machine_id = next((c["value"] for c in cookies if c["name"] == "segMachineId"), "unknown")
        
        file_id = 3441252
        print(f"1. Solicitando URL de descarga para fileId={file_id} (DOCUMENTO NUEVO NO VISTO)...")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token_cookie}",
            "Referer": "https://wuolah.com/",
            "x-seg-machine-id": machine_id,
        }
        payload = {
            "fileId": file_id,
            "adblockDetected": False,
            "noAdsWithCoins": False,
            "avoidFallback": False
        }
        
        t0 = asyncio.get_event_loop().time()
        resp = await page.request.post(
            "https://api.wuolah.com/v2/download",
            data=json.dumps(payload),
            headers=headers
        )
        t_api = asyncio.get_event_loop().time() - t0
        print(f"   API response en {t_api:.2f}s | Status: {resp.status}")
        
        data = await resp.json()
        pdf_url = data.get("url")
        print(f"2. URL de descarga obtenida: {pdf_url[:80]}...")
        
        print("3. Descargando bytes directos de CloudFront...")
        t0 = asyncio.get_event_loop().time()
        pdf_resp = await page.request.get(pdf_url)
        t_dl = asyncio.get_event_loop().time() - t0
        pdf_bytes = await pdf_resp.body()
        print(f"   Descarga completada en {t_dl:.2f}s | Status: {pdf_resp.status} | Bytes: {len(pdf_bytes)}")
        
        print("4. Analizando y validando PDF con nuestro pipeline...")
        analysis = PdfAnalyzer.analyze(pdf_bytes)
        print(f"   Analysis: detected_type={analysis.get('detected_type')}, size={analysis.get('size_bytes')}")
        
        normalizer = DefaultNormalizer()
        normalized_bytes = normalizer.normalize(pdf_bytes)
        print(f"   Normalization: output_size={len(normalized_bytes)}")
        
        val_res = PdfValidator.validate(normalized_bytes)
        print(f"   Validation result: {val_res}")
        
        await ctx.close()

if __name__ == "__main__":
    asyncio.run(test_full_pipeline_direct())

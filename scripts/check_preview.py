import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from backend.core.config import settings

async def check_preview_and_clean():
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
            "Accept": "application/json"
        }
        
        # Test preview for 14080870
        file_id = 14080870
        print(f"1. Consultando GET /v2/preview?fileId={file_id}...")
        resp = await page.request.get(f"https://api.wuolah.com/v2/preview?fileId={file_id}", headers=headers)
        print("Status GET /v2/preview:", resp.status)
        try:
            data = await resp.json()
            print("Preview keys:", list(data.keys()))
            urls = data.get("urls", [])
            print(f"Total preview URLs: {len(urls)}")
            for idx, u in enumerate(urls[:3]):
                print(f"  [{idx}] {u[:80]}...")
        except Exception as e:
            print("Error preview json:", e)
            
        # Test POST /v2/preview
        print(f"\n2. Consultando POST /v2/preview...")
        post_resp = await page.request.post(
            "https://api.wuolah.com/v2/preview",
            data=json.dumps({"fileId": file_id}),
            headers={"Content-Type": "application/json", **headers}
        )
        print("Status POST /v2/preview:", post_resp.status)
        try:
            pdata = await post_resp.json()
            print("POST preview keys:", list(pdata.keys()))
            purls = pdata.get("urls", [])
            print(f"Total POST preview URLs: {len(purls)}")
            for idx, u in enumerate(purls[:3]):
                print(f"  [{idx}] {u[:80]}...")
        except Exception as e:
            print("Error POST preview json:", e)

        await ctx.close()

if __name__ == "__main__":
    asyncio.run(check_preview_and_clean())

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from backend.core.config import settings

async def test_clean_endpoints():
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
        
        doc_id = 14080870
        upload_id = 6668738
        
        test_urls = [
            f"https://api.wuolah.com/v2/documents/{doc_id}/file",
            f"https://api.wuolah.com/v2/documents/{doc_id}/download",
            f"https://api.wuolah.com/v2/uploads/{upload_id}",
            f"https://api.wuolah.com/v2/uploads/{upload_id}/file",
            f"https://api.wuolah.com/v2/me/document/{doc_id}/download",
            f"https://api.wuolah.com/v2/me/document/{doc_id}",
        ]
        
        for u in test_urls:
            resp = await page.request.get(u, headers=headers)
            print(f"GET {u} -> Status: {resp.status}")
            if resp.status == 200:
                ct = resp.headers.get("content-type", "")
                print(f"   Content-Type: {ct}")
                if "json" in ct:
                    j = await resp.json()
                    print(f"   Keys: {list(j.keys()) if isinstance(j, dict) else len(j)}")
                    print(f"   Sample: {str(j)[:200]}")
                elif "pdf" in ct or "octet" in ct:
                    b = await resp.body()
                    print(f"   Bytes: {len(b)}")

        # Also test POST /v2/download with different parameters!
        # What happens if we pass "noAdsWithCoins": True or ads: [] or promo options?
        print("\n--- TEST POST /v2/download OPTIONS ---")
        options = [
            {"fileId": doc_id, "noAdsWithCoins": True},
            {"fileId": doc_id, "noAdsWithCoins": False, "avoidFallback": True},
            {"fileId": doc_id, "noAdsWithCoins": False, "adblockDetected": True},
        ]
        for opt in options:
            post_resp = await page.request.post(
                "https://api.wuolah.com/v2/download",
                data=json.dumps(opt),
                headers={"Content-Type": "application/json", **headers}
            )
            print(f"POST /v2/download {opt} -> Status: {post_resp.status}")
            if post_resp.status == 200:
                pj = await post_resp.json()
                print("   downloadId:", pj.get("downloadId"))
                print("   url:", pj.get("url")[:80] if pj.get("url") else None)
                print("   isEncrypted:", pj.get("isEncrypted"))
                print("   renderedAds:", len(pj.get("renderedAds", [])))

        await ctx.close()

if __name__ == "__main__":
    asyncio.run(test_clean_endpoints())

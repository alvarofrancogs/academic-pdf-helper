import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from backend.core.config import settings

async def test():
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
        
        # 1. Retrieve the auth token from cookies
        cookies = await ctx.cookies("https://wuolah.com")
        token_cookie = next((c["value"] for c in cookies if c["name"] == "token"), None)
        machine_id_cookie = next((c["value"] for c in cookies if c["name"] == "segMachineId"), "unknown")
        print(f"Token obtenido de cookie: {token_cookie[:35]}... (longitud {len(token_cookie) if token_cookie else 0})")
        print(f"segMachineId: {machine_id_cookie}")
        
        waited_time = await page.evaluate("() => localStorage.getItem('download-waited-time')")
        print(f"localStorage['download-waited-time']: {waited_time}")

        # 2. Test Calling POST /v2/download with Authorization header:
        # A) First with minimal payload: only fileId!
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token_cookie}",
            "Referer": "https://wuolah.com/",
            "x-seg-machine-id": machine_id_cookie,
        }
        
        payload_1 = {
            "fileId": 14080870,
            "adblockDetected": False,
            "noAdsWithCoins": False,
            "avoidFallback": False
        }
        print("\n--- TEST 1: Llamada a POST /v2/download con payload mínimo ---")
        resp1 = await page.request.post(
            "https://api.wuolah.com/v2/download",
            data=json.dumps(payload_1),
            headers=headers
        )
        print("Status Test 1:", resp1.status)
        text1 = await resp1.text()
        print("Respuesta Test 1:", text1[:400])
        
        # If Test 1 didn't work, what did it say?
        # Let's test with full payload structure (ads: [], etc.)
        if resp1.status != 200:
            payload_2 = {
                "fileId": 14080870,
                "adblockDetected": False,
                "noAdsWithCoins": False,
                "avoidFallback": False,
                "machineId": machine_id_cookie,
                "ads": [],
                "fallbackAds": []
            }
            print("\n--- TEST 2: Llamada con ads vacíos ---")
            resp2 = await page.request.post(
                "https://api.wuolah.com/v2/download",
                data=json.dumps(payload_2),
                headers=headers
            )
            print("Status Test 2:", resp2.status)
            text2 = await resp2.text()
            print("Respuesta Test 2:", text2[:400])
            
        await ctx.close()

if __name__ == "__main__":
    asyncio.run(test())

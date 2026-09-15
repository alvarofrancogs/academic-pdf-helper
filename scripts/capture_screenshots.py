import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def capture():
    output_dir = Path("docs/assets")
    output_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 840},
            device_scale_factor=2
        )
        page = await context.new_page()
        await page.goto("http://localhost:8000/", wait_until="networkidle")
        await asyncio.sleep(1)

        # 1. Main screen
        main_path = output_dir / "preview-main.png"
        await page.screenshot(path=str(main_path))
        print(f"Captured: {main_path}")

        # 2. Click on 'Cómo funciona'
        modal_btn = page.locator("text=Cómo funciona").first
        if await modal_btn.count() > 0:
            await modal_btn.click()
            await asyncio.sleep(0.6)  # wait for 350ms transition
            modal_path = output_dir / "preview-modal.png"
            await page.screenshot(path=str(modal_path))
            print(f"Captured: {modal_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture())

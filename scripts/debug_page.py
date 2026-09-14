import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playwright.async_api import async_playwright
from backend.core.config import settings

async def check():
    profile_dir = settings.temp_path / "browser_profile"
    target_url = "https://wuolah.com/apuntes/sistemas-operativos-i/preguntas-examen-ssoo-i-pdf-14080870"
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        print("Navigating...")
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)
        
        elements = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('button, a, [role="button"], [data-testid]')).map(el => {
                return {
                    tag: el.tagName,
                    text: (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' '),
                    id: el.id,
                    className: (typeof el.className === 'string') ? el.className : '',
                    dataTestId: el.getAttribute('data-testid'),
                    ariaLabel: el.getAttribute('aria-label'),
                    role: el.getAttribute('role'),
                    href: el.getAttribute('href')
                };
            }).filter(item => {
                const t = item.text.toLowerCase();
                return t.includes('descarga') || t.includes('publi') || t.includes('gratis') || t.includes('coin') || t.includes('pdf');
            });
        }""")
        print(f"Matching elements count: {len(elements)}")
        for el in elements:
            print(json.dumps(el, ensure_ascii=False))
            
        cookies = await ctx.cookies("https://wuolah.com")
        print("Total cookies on wuolah.com:", len(cookies))
        print("Cookie names:", [c["name"] for c in cookies])
        await ctx.close()

if __name__ == "__main__":
    asyncio.run(check())

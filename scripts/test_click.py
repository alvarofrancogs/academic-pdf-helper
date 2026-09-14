import asyncio
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from backend.core.config import settings
from backend.browser.network_debugger import NetworkDebugger

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_click")

async def test():
    profile_dir = settings.temp_path / "browser_profile"
    target_url = "https://wuolah.com/apuntes/sistemas-operativos-i/preguntas-examen-ssoo-i-pdf-14080870"
    
    debugger = NetworkDebugger(name="click_test")
    
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        debugger.attach_to_context(ctx)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        debugger.attach_to_page(page)
        
        logger.info("Navegando al documento...")
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)
        
        # Look for the button
        btn = page.locator("button").filter(has_text="Descarga PDF con publi").first
        count = await btn.count()
        logger.info(f"Botón 'Descarga PDF con publi' encontrado: {count > 0}")
        
        if count > 0:
            logger.info("Haciendo click en 'Descarga PDF con publi'...")
            # Set up expect_download just in case
            try:
                await btn.click()
                logger.info("Click realizado.")
            except Exception as e:
                logger.error(f"Error al hacer click: {e}")
                
        # Wait and observe DOM and network
        for sec in range(15):
            await asyncio.sleep(1)
            # Check for any modals or countdowns or download triggers
            modals = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('.modal, [role="dialog"], [class*="modal"], [class*="popup"], [class*="dialog"]')).map(m => (m.innerText || '').slice(0, 200));
            }""")
            if modals:
                logger.info(f"[{sec}s] Modales visibles: {modals}")
            
            # Check if there are any new buttons
            new_btns = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('button, a')).map(b => (b.innerText || '').trim()).filter(t => t.length > 0 && t.length < 50);
            }""")
            # Print if any download-related button appeared
            dl_btns = [b for b in new_btns if any(w in b.lower() for w in ['descarga', 'publi', 'anuncio', 'saltar', 'espera', 'segundo', 'ahora'])]
            logger.info(f"[{sec}s] Botones relevantes: {dl_btns}")

        logger.info(f"Eventos capturados: {len(debugger.events)}")
        debugger.export_trace_json(Path("artifacts/test_click_trace.json"))
        debugger.export_summary_text(Path("artifacts/test_click_summary.txt"))
        await ctx.close()

if __name__ == "__main__":
    asyncio.run(test())

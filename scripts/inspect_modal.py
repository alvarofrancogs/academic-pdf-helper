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
logger = logging.getLogger("inspect_modal")

async def inspect():
    profile_dir = settings.temp_path / "browser_profile"
    target_url = "https://wuolah.com/apuntes/sistemas-operativos-i/preguntas-examen-ssoo-i-pdf-14080870"
    
    debugger = NetworkDebugger(name="modal_inspection")
    
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
        
        logger.info("Navegando a Wuolah...")
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)
        
        btn = page.locator("button").filter(has_text="Descarga PDF con publi").first
        if await btn.count() > 0:
            logger.info("Click en 'Descarga PDF con publi'...")
            await btn.click()
            await asyncio.sleep(2)
            
            # Inspect modal elements in detail
            modal_details = await page.evaluate("""() => {
                const dialogs = Array.from(document.querySelectorAll('.modal, [role="dialog"], [class*="modal"]'));
                return dialogs.map(d => {
                    const buttons = Array.from(d.querySelectorAll('button, a, div[role="button"]')).map(b => ({
                        tag: b.tagName,
                        text: (b.innerText || b.textContent || '').trim().replace(/\\s+/g, ' '),
                        disabled: b.disabled || b.getAttribute('aria-disabled') || false,
                        className: b.className,
                        id: b.id
                    }));
                    return {
                        html: d.outerHTML.slice(0, 1000),
                        buttons: buttons
                    };
                });
            }""")
            logger.info(f"Detalles de modales: {json.dumps(modal_details, indent=2, ensure_ascii=False)}")
            
            # Let's see if clicking 'Continuar' does anything or if it's disabled
            continuar_btn = page.locator("button, a").filter(has_text="Continuar").first
            if await continuar_btn.count() > 0:
                is_disabled = await continuar_btn.is_disabled()
                is_visible = await continuar_btn.is_visible()
                logger.info(f"'Continuar' visible={is_visible}, disabled={is_disabled}")
                if is_visible and not is_disabled:
                    logger.info("Intentando click en 'Continuar'...")
                    try:
                        await continuar_btn.click(timeout=3000)
                        logger.info("Click en 'Continuar' realizado con éxito.")
                    except Exception as e:
                        logger.error(f"Error al pulsar 'Continuar': {e}")
            
            # Now let's observe for 65 seconds until countdown finishes, logging every 5s
            logger.info("Iniciando observación del countdown hasta 70 segundos...")
            for sec in range(0, 70, 5):
                await asyncio.sleep(5)
                status_info = await page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button, a')).map(b => ({
                        text: (b.innerText || '').trim(),
                        disabled: b.disabled || false
                    })).filter(b => b.text.length > 0 && b.text.length < 50);
                    
                    const textContent = document.body.innerText.slice(0, 500);
                    return { btns, textPreview: textContent.split('\\n').slice(0, 10) };
                }""")
                logger.info(f"[{sec+5}s] Botones en pantalla: {[b['text'] for b in status_info['btns'] if any(k in b['text'].lower() for k in ['descarg', 'publi', 'continuar', 'anuncio', 'ahora', 'saltar', 'preparando'])]}")
                
                # Check if download or API call was recorded
                wuolah_api = [e for e in debugger.events if 'api.wuolah.com' in e.get('url', '') and e.get('method') in ['POST', 'GET'] and 'download' in e.get('url', '').lower()]
                if wuolah_api:
                    logger.info(f"¡DETECTADA PETICIÓN DE DESCARGA!: {wuolah_api}")
                if debugger.downloads:
                    logger.info(f"¡DETECTADA DESCARGA PLAYWRIGHT!: {debugger.downloads}")
                    break

        debugger.export_trace_json(Path("artifacts/modal_trace.json"))
        debugger.export_summary_text(Path("artifacts/modal_summary.txt"))
        await ctx.close()

if __name__ == "__main__":
    asyncio.run(inspect())

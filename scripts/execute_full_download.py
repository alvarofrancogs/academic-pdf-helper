import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from backend.core.config import settings
from backend.browser.network_debugger import NetworkDebugger

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("full_download")

TARGET_URL = "https://wuolah.com/apuntes/sistemas-operativos-i/preguntas-examen-ssoo-i-pdf-14080870"
ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR = settings.temp_path / "browser_profile"


async def run_full_authorized_download():
    logger.info("=== INICIANDO CAPTURA COMPLETA DE FLUJO DE DESCARGA AUTORIZADA ===")
    debugger = NetworkDebugger(name="authorized_download_full")

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        debugger.attach_to_context(ctx)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        debugger.attach_to_page(page)

        logger.info(f"Navegando al documento: {TARGET_URL}")
        await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)

        # 1. Click "Descarga PDF con publi"
        btn_con_publi = page.locator("button").filter(has_text="Descarga PDF con publi").first
        if await btn_con_publi.count() == 0:
            logger.error("No se encontró el botón 'Descarga PDF con publi'")
            return

        logger.info("Paso 1: Pulsando 'Descarga PDF con publi'...")
        await btn_con_publi.click()
        await asyncio.sleep(2)

        # 2. Wait for the modal button to transition from "Continuar" (disabled) to "Descargar" (enabled)
        logger.info("Paso 2: Esperando a que el temporizador termine y el botón pase a 'Descargar'...")
        descargar_btn = None
        for i in range(70):
            # Check if button with text "Descargar" appeared in modal
            modal_btn = page.locator(".MaterialBaseUIModal_materialBaseUIModalPopup__N63K3 button, [role='dialog'] button, .PreDownloadModal_modalContent__BlGnb button").filter(has_text="Descargar").first
            if await modal_btn.count() > 0:
                is_disabled = await modal_btn.is_disabled()
                if not is_disabled:
                    descargar_btn = modal_btn
                    logger.info(f"¡Botón 'Descargar' activo y habilitado detectado tras {i} segundos!")
                    break
            
            if i % 5 == 0:
                logger.info(f"Esperando cuenta atrás... ({i}s)")
            await asyncio.sleep(1)

        if not descargar_btn:
            logger.warning("No se detectó el botón específico dentro del modal, buscando en toda la página...")
            descargar_btn = page.locator("button:has-text('Descargar')").first

        # 3. Click "Descargar" and capture download event and subsequent requests
        logger.info("Paso 3: Pulsando 'Descargar' en el modal de Wuolah...")
        download_info = None
        try:
            async with page.expect_download(timeout=15000) as download_catcher:
                await descargar_btn.click()
                logger.info("Click en 'Descargar' ejecutado. Esperando evento download...")
                download = await download_catcher.value
                download_info = {
                    "url": download.url,
                    "suggested_filename": download.suggested_filename,
                    "path": await download.path()
                }
                logger.info(f"¡EVENTO DOWNLOAD CAPTURADO!: {download_info}")
        except Exception as e:
            logger.warning(f"expect_download finalizó o no se produjo mediante evento nativo: {e}")

        # 4. Wait an extra 10 seconds to capture all remaining network responses, redirects, and CDN fetches
        logger.info("Paso 4: Esperando 10 segundos adicionales para registrar todas las peticiones secundarias...")
        await asyncio.sleep(10)

        # 5. Check if any new tabs opened
        logger.info(f"Páginas abiertas en context: {len(ctx.pages)}")
        for idx, p_item in enumerate(ctx.pages):
            logger.info(f"  Página {idx}: {p_item.url}")

        # 6. Export trace and summary
        debugger.export_trace_json(ARTIFACTS_DIR / "network_trace.json")
        debugger.export_summary_text(ARTIFACTS_DIR / "network_summary.txt")
        logger.info(f"Captura finalizada: {len(debugger.events)} eventos, {len(debugger.downloads)} descargas registradas.")
        await ctx.close()

if __name__ == "__main__":
    asyncio.run(run_full_authorized_download())

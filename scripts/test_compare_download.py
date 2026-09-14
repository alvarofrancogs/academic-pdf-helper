import asyncio
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz  # PyMuPDF
from playwright.async_api import async_playwright
from backend.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("compare_download")

TARGET_URL = "https://wuolah.com/apuntes/fundamentos-de-computadores/apuntes-fc-fc-teoria-practica-parte-2-pdf-11877090"
# Notice: our past job for this document (c0395bc8119c) got only 6 pages!

async def run():
    profile_dir = settings.temp_path / "browser_profile"
    
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        
        preview_data = None
        download_data = None
        
        async def on_response(resp):
            nonlocal preview_data
            if "preview.pdf" in resp.url and resp.status == 200:
                body = await resp.body()
                preview_data = (resp.url, body)
                logger.info(f"[RESPONSE] Preview captured: {resp.url} ({len(body)} bytes)")

        page.on("response", on_response)
        
        logger.info(f"1. Navegando a {TARGET_URL}...")
        await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)
        
        # Check preview pages if captured
        if preview_data:
            url, b = preview_data
            doc = fitz.open(stream=b, filetype="pdf")
            logger.info(f"--> PREVIEW.PDF TIENE: {len(doc)} páginas ({len(b)} bytes)")
            doc.close()

        # Dismiss cookie/consent banners including Google Funding Choices
        consent_selectors = [
            ".fc-consent-root button.fc-cta-consent",
            ".fc-consent-root button.fc-primary-button",
            "button:has-text('Consentir')",
            "button:has-text('Acepto')",
            "#onetrust-accept-btn-handler",
            "button:has-text('Aceptar todas')",
            "button:has-text('Aceptar')",
        ]
        for sel in consent_selectors:
            try:
                b = page.locator(sel).first
                if await b.count() > 0 and await b.is_visible():
                    logger.info(f"Dismissing consent banner with: {sel}")
                    await b.click(timeout=2000)
                    await asyncio.sleep(1)
                    break
            except Exception:
                pass
            
        # 2. Click "Descarga PDF con publi"
        btn = page.locator("button").filter(has_text="Descarga PDF con publi").first
        if await btn.count() == 0:
            logger.error("No se encontró el botón 'Descarga PDF con publi'")
            btn = page.locator("button:has-text('Descarga')").first
            
        logger.info("2. Pulsando botón de descarga...")
        await btn.click(force=True)
        await asyncio.sleep(2)
        
        # 3. Wait for countdown
        logger.info("3. Esperando cuenta atrás de publicidad en el modal...")
        descargar_btn = None
        for i in range(75):
            modal_btn = page.locator("button").filter(has_text="Descargar").first
            if await modal_btn.count() > 0:
                is_disabled = await modal_btn.is_disabled()
                is_visible = await modal_btn.is_visible()
                if is_visible and not is_disabled:
                    descargar_btn = modal_btn
                    logger.info(f"¡Botón 'Descargar' listo tras {i}s!")
                    break
            if i % 5 == 0:
                logger.info(f"   Esperando... {i}s")
            await asyncio.sleep(1)
            
        if not descargar_btn:
            logger.error("No se encontró o habilitó el botón 'Descargar'")
            await ctx.close()
            return
            
        # 4. Click Descargar and expect download
        logger.info("4. Pulsando 'Descargar' y esperando evento de descarga...")
        try:
            async with page.expect_download(timeout=30000) as dl_catcher:
                await descargar_btn.click()
                dl = await dl_catcher.value
                path = await dl.path()
                logger.info(f"¡Descarga capturada!: {dl.suggested_filename}, url: {dl.url}")
                with open(path, "rb") as f:
                    raw_dl = f.read()
                
                # Check magic bytes
                if raw_dl.startswith(b"%PDF"):
                    doc_dl = fitz.open(stream=raw_dl, filetype="pdf")
                    logger.info(f"--> DOCUMENTO COMPLETO DESCARGADO: {len(doc_dl)} páginas ({len(raw_dl)} bytes)")
                    doc_dl.close()
                elif bytes([b ^ 27 for b in raw_dl[:4]]) == b"%PDF":
                    clean = bytes([b ^ 27 for b in raw_dl])
                    doc_dl = fitz.open(stream=clean, filetype="pdf")
                    logger.info(f"--> DOCUMENTO COMPLETO OFUSCADO (XOR 27) DESCARGADO: {len(doc_dl)} páginas ({len(clean)} bytes)")
                    doc_dl.close()
                else:
                    logger.info(f"--> Descarga formato desconocido: {raw_dl[:20]}")
        except Exception as e:
            logger.error(f"Error esperando descarga: {e}")
            
        await ctx.close()

if __name__ == "__main__":
    asyncio.run(run())

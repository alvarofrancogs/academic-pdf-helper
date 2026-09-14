import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.browser.wuolah import WuolahBrowser
from backend.pdf.analyzer import PdfAnalyzer
from backend.pdf.default_normalizer import DefaultNormalizer
from backend.pdf.validator import PdfValidator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_browser")

TARGET_URL = "https://wuolah.com/apuntes/sistemas-operativos-i/preguntas-examen-ssoo-i-pdf-14080870"

async def test_wuolah_browser_real():
    browser = WuolahBrowser(headless=True)
    try:
        logger.info(f"1. Abriendo documento en WuolahBrowser: {TARGET_URL}")
        t0 = asyncio.get_event_loop().time()
        await browser.open_document(TARGET_URL)
        t_open = asyncio.get_event_loop().time() - t0
        logger.info(f"   Página abierta en {t_open:.2f}s")
        
        logger.info("2. Buscando recurso del documento (activando Fast-Path)...")
        t0 = asyncio.get_event_loop().time()
        resource = await browser.find_document_resource(timeout_seconds=20)
        t_resource = asyncio.get_event_loop().time() - t0
        logger.info(f"   ¡Recurso capturado en {t_resource:.2f}s!")
        logger.info(f"   Filename: {resource.filename}")
        logger.info(f"   Content-Type: {resource.content_type}")
        logger.info(f"   Bytes: {resource.size_bytes}")
        
        logger.info("3. Verificando pipeline de normalización y validación...")
        analysis = PdfAnalyzer.analyze(resource.data)
        logger.info(f"   Análisis: {analysis.get('detected_type')}")
        
        normalizer = DefaultNormalizer()
        clean_bytes = normalizer.normalize(resource.data)
        
        val_result = PdfValidator.validate(clean_bytes)
        logger.info(f"   Resultado de validación: {val_result}")
        assert val_result["valid"] is True, f"Error en validación: {val_result.get('errors')}"
        logger.info("4. ¡VERIFICACIÓN EXITOSA AL 100%! Documento procesado y validado en tiempo récord.")
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_wuolah_browser_real())

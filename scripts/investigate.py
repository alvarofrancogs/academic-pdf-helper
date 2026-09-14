import asyncio
import json
import logging
from pathlib import Path
import sys

# Ensure workspace root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright

from backend.browser.network_debugger import NetworkDebugger
from backend.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("investigate")

TARGET_URL = "https://wuolah.com/apuntes/sistemas-operativos-i/preguntas-examen-ssoo-i-pdf-14080870"
ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR = settings.temp_path / "browser_profile"


async def run_prueba_a() -> NetworkDebugger:
    """PRUEBA A: Abrir el documento sin pulsar descargar."""
    logger.info("=== INICIANDO PRUEBA A: Navegación y carga sin pulsar descarga ===")
    debugger = NetworkDebugger(name="prueba_a_visit")

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        debugger.attach_to_context(ctx)

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        debugger.attach_to_page(page)

        logger.info(f"Navegando a {TARGET_URL}...")
        await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)

        # Wait 10 seconds to collect baseline network activity
        await asyncio.sleep(10)

        debugger.export_trace_json(ARTIFACTS_DIR / "network_trace_a.json")
        debugger.export_summary_text(ARTIFACTS_DIR / "network_summary_a.txt")
        logger.info(f"PRUEBA A completada: {len(debugger.events)} eventos capturados.")
        await ctx.close()

    return debugger


async def run_prueba_b() -> NetworkDebugger:
    """PRUEBA B: Pulsar 'Descarga PDF con publi' y registrar la red durante la descarga."""
    logger.info("=== INICIANDO PRUEBA B: Interacción y descarga con publicidad ===")
    debugger = NetworkDebugger(name="prueba_b_download")

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        debugger.attach_to_context(ctx)

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        debugger.attach_to_page(page)

        logger.info(f"Navegando a {TARGET_URL}...")
        await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)

        # Close any coin or subscription modals that might be lingering
        await page.keyboard.press("Escape")

        logger.info("Buscando botón 'Descarga PDF con publi'...")
        clicked_info = await page.evaluate("""() => {
            const elements = Array.from(document.querySelectorAll('button, a, div[role="button"], [data-testid*="download"]'));
            for (const el of elements) {
                const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                if (txt.includes('sin publi') || txt.includes('sin publicidad') || txt.includes('sin anuncios') || 
                    txt.includes('turbo') || txt.includes('pro') || txt.includes('suscrip')) {
                    continue;
                }
                if (txt.includes('con publi') || txt.includes('con publicidad') || txt.includes('con anuncios') || txt.includes('gratis')) {
                    el.click();
                    return { clicked: true, text: txt };
                }
            }
            // Secondary search
            for (const el of elements) {
                const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                if (txt.includes('descarga') && !txt.includes('sin publi') && !txt.includes('turbo')) {
                    el.click();
                    return { clicked: true, text: txt };
                }
            }
            return { clicked: false };
        }""")

        logger.info(f"Resultado clic inicial: {clicked_info}")
        await asyncio.sleep(2)

        # Check if modal opened asking for confirmation
        modal_info = await page.evaluate("""() => {
            const modalButtons = Array.from(document.querySelectorAll('.modal button, [role="dialog"] button, button'));
            for (const btn of modalButtons) {
                const txt = (btn.innerText || btn.textContent || '').trim().toLowerCase();
                if (txt.includes('sin publi') || txt.includes('sin publicidad') || txt.includes('turbo') || txt.includes('pro')) continue;
                if (txt.includes('con publi') || txt.includes('con publicidad') || txt.includes('anuncio') || txt.includes('gratis') || txt.includes('continuar')) {
                    btn.click();
                    return { clicked: true, text: txt };
                }
            }
            return { clicked: false };
        }""")
        logger.info(f"Resultado clic modal: {modal_info}")

        # Wait 25 seconds observing all requests (ad countdowns, API calls, CDN streams, downloads)
        logger.info("Observando red durante 25 segundos...")
        for i in range(25):
            # Check if an ad countdown finished and shows "Descargar ahora" or "Saltar"
            try:
                await page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button, a'));
                    for (const b of btns) {
                        const t = (b.innerText || '').toLowerCase();
                        if (t.includes('descargar ahora') || t.includes('saltar y descargar') || t.includes('descargar archivo')) {
                            b.click();
                            break;
                        }
                    }
                }""")
            except Exception:
                pass
            await asyncio.sleep(1)

        debugger.export_trace_json(ARTIFACTS_DIR / "network_trace_b.json")
        debugger.export_summary_text(ARTIFACTS_DIR / "network_summary_b.txt")
        logger.info(f"PRUEBA B completada: {len(debugger.events)} eventos capturados, {len(debugger.downloads)} descargas.")
        await ctx.close()

    return debugger


def compare_and_generate_artifacts(trace_a: NetworkDebugger, trace_b: NetworkDebugger):
    """Compara Prueba A con Prueba B para aislar las peticiones exclusivas de la descarga."""
    urls_a = {ev.get("url") for ev in trace_a.events if ev.get("url")}
    
    exclusive_events = []
    for ev in trace_b.events:
        url = ev.get("url")
        # Keep if URL is new or is a POST/PUT or has PDF/binary/JSON content
        if ev.get("event_type") == "download":
            exclusive_events.append(ev)
        elif url and url not in urls_a:
            exclusive_events.append(ev)
        elif ev.get("is_pdf") or ev.get("is_binary"):
            exclusive_events.append(ev)

    # Save unified network_trace.json
    trace_json_path = ARTIFACTS_DIR / "network_trace.json"
    with open(trace_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "target_url": TARGET_URL,
            "prueba_a_total_events": len(trace_a.events),
            "prueba_b_total_events": len(trace_b.events),
            "exclusive_download_events_count": len(exclusive_events),
            "downloads": trace_b.downloads,
            "new_pages": trace_b.new_pages,
            "exclusive_download_events": exclusive_events,
            "full_trace_b": trace_b.events,
        }, f, indent=2, ensure_ascii=False)
    logger.info(f"Guardado {trace_json_path}")

    # Save formatted network_summary.txt
    summary_path = ARTIFACTS_DIR / "network_summary.txt"
    lines = [
        "=== NETWORK TRACE ===",
        f"Documento analizado: {TARGET_URL}",
        f"Eventos totales Prueba A (sólo ver): {len(trace_a.events)}",
        f"Eventos totales Prueba B (descarga): {len(trace_b.events)}",
        f"Descargas capturadas: {len(trace_b.downloads)}",
        f"Pestañas nuevas detectadas: {len(trace_b.new_pages)}",
        "",
        "--- SECUENCIA DE PETICIONES EXCLUSIVAS DE LA DESCARGA ---",
        "",
    ]

    counter = 1
    for ev in exclusive_events:
        ev_type = ev.get("event_type")
        if ev_type == "response":
            method = ev.get("method", "GET")
            url = ev.get("url", "")
            status = ev.get("status", 0)
            res_type = ev.get("resource_type", "other")
            ctype = ev.get("content_type", "unknown").split(";")[0]

            lines.append(f"[{counter}] {method:<4} {url}")
            lines.append(f"    type={res_type}")
            lines.append(f"    status={status}")
            lines.append(f"    content-type={ctype}")

            if ev.get("redirect_chain"):
                chain = " -> ".join([r["url"] for r in ev["redirect_chain"]] + [url])
                lines.append(f"    redirect_chain={chain}")

            if ev.get("json_keys"):
                lines.append(f"    json_keys={ev['json_keys']}")

            if ev.get("is_pdf"):
                lines.append(f"    is_pdf=True | size={ev.get('size_bytes')} bytes | starts_with_pdf={ev.get('starts_with_pdf')}")

            if ev.get("is_binary"):
                lines.append(f"    is_binary=True | size={ev.get('size_bytes')} bytes | xor27_magic={ev.get('starts_with_xor27')}")

            lines.append("")
            counter += 1

        elif ev_type == "download":
            lines.append(f"[{counter}] DOWNLOAD")
            lines.append(f"    url={ev.get('url')}")
            lines.append(f"    suggested_filename={ev.get('suggested_filename')}")
            lines.append("")
            counter += 1

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"Guardado {summary_path}")


async def main():
    logger.info("Iniciando investigación técnica de red de Wuolah...")
    trace_a = await run_prueba_a()
    trace_b = await run_prueba_b()
    compare_and_generate_artifacts(trace_a, trace_b)
    logger.info("Investigación completada exitosamente.")


if __name__ == "__main__":
    from datetime import datetime, timezone
    asyncio.run(main())

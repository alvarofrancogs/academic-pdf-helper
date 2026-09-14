import asyncio
import base64
import io
import json
import logging
import re
import urllib.request
from typing import List, Optional
from urllib.parse import urlparse

import pypdf
from playwright.async_api import Browser, BrowserContext, Page, Response, async_playwright, Playwright

from backend.browser.resource import DocumentResource
from backend.core.config import settings
from backend.core.security import validate_wuolah_url, extract_wuolah_file_id, SecurityError

logger = logging.getLogger("wuolah.browser")


class WuolahBrowserError(Exception):
    """Raised when browser automation encounters an error."""
    pass


class WuolahBrowser:
    """
    Playwright-based browser controller for Wuolah interactions.
    Handles interactive user login, document navigation, and network resource interception.
    """

    def __init__(self, headless: Optional[bool] = None):
        self.headless = headless if headless is not None else settings.BROWSER_HEADLESS
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._intercepted_resources: List[DocumentResource] = []
        self._resource_event: asyncio.Event = asyncio.Event()
        self._current_doc_url: Optional[str] = None
        self._current_doc_metadata: dict = {}
        self._expected_pages: Optional[int] = None

    async def start(self) -> None:
        """Launch Chromium and configure persistent browser context for session retention."""
        if self._playwright is None:
            self._playwright = await async_playwright().start()

        # If context was closed or disconnected, reset so we re-launch cleanly
        if self._context is not None:
            try:
                _ = self._context.pages
            except Exception:
                self._context = None
                self._page = None

        if self._context is None:
            profile_dir = settings.temp_path / "browser_profile"
            profile_dir.mkdir(parents=True, exist_ok=True)
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
            if not self.headless:
                launch_args.append("--start-maximized")

            try:
                self._context = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    headless=self.headless,
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/128.0.0.0 Safari/537.36"
                    ),
                    accept_downloads=True,
                    no_viewport=True if not self.headless else False,
                    viewport={"width": 1280, "height": 800} if self.headless else None,
                    args=launch_args,
                )
            except Exception as e:
                logger.warning(f"Reintentando inicio de navegador tras error de bloqueo: {e}")
                # Clean stale lockfile if orphaned
                lock_file = profile_dir / "lockfile"
                if lock_file.exists():
                    try:
                        lock_file.unlink()
                    except Exception:
                        pass
                self._context = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    headless=self.headless,
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/128.0.0.0 Safari/537.36"
                    ),
                    accept_downloads=True,
                    no_viewport=True if not self.headless else False,
                    viewport={"width": 1280, "height": 800} if self.headless else None,
                    args=launch_args,
                )

            await self._context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                if (navigator.userAgentData) {
                    Object.defineProperty(navigator, 'userAgentData', {
                        get: () => ({
                            brands: [
                                {brand: 'Google Chrome', version: '128'},
                                {brand: 'Chromium', version: '128'},
                                {brand: 'Not=A?Brand', version: '24'}
                            ],
                            mobile: false,
                            platform: 'Windows'
                        })
                    });
                }
            """)
            await self._inject_auth_cookies()

            self._context.on("page", self._attach_listeners)
            for p in self._context.pages:
                self._attach_listeners(p)
            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        elif self._page is None or self._page.is_closed():
            try:
                self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
                self._attach_listeners(self._page)
            except Exception:
                # If context is closed, recreate cleanly
                await self.close()
                await self.start()

    def _attach_listeners(self, page: Page) -> None:
        """Attach network response and download listeners to capture candidate document resources."""
        page.on("response", self._on_response)
        page.on("download", self._on_download)

    async def _on_response(self, response: Response) -> None:
        """Inspect network responses to capture raw document resources."""
        try:
            url = response.url
            status = response.status
            if status < 200 or status >= 300:
                return

            headers = response.headers
            content_type = headers.get("content-type", "").lower()
            content_length = int(headers.get("content-length", 0)) if headers.get("content-length") else 0
            content_disp = headers.get("content-disposition", "")

            # Identify if this response corresponds to a document or download API
            is_pdf_content = "application/pdf" in content_type or "application/octet-stream" in content_type or "binary" in content_type
            is_pdf_extension = ".pdf" in url.lower().split("?")[0]
            cdn_matches = ["storage.googleapis.com", "cloudfront.net", "wuolah", "amazonaws.com", "s3"]
            is_cdn_document = any(cdn in url.lower() for cdn in cdn_matches) and (
                is_pdf_content or is_pdf_extension or "download" in url.lower() or content_length > 10000
            )

            # Check if this is a Wuolah download API endpoint returning a JSON with download URL
            if "download" in url.lower() and "application/json" in content_type:
                try:
                    json_data = await response.json()
                    direct_url = json_data.get("url") or json_data.get("download_url") or json_data.get("data", {}).get("url")
                    if direct_url and isinstance(direct_url, str) and direct_url.startswith("http"):
                        logger.info(f"Detectada URL de descarga en API de Wuolah: {direct_url[:80]}...")
                        # Fetch the direct document bytes using the browser request context (with session)
                        doc_resp = await self._page.request.get(direct_url)
                        if doc_resp.ok:
                            raw_bytes = await doc_resp.body()
                            if len(raw_bytes) > 500:
                                resource = DocumentResource(
                                    url=direct_url,
                                    content_type=doc_resp.headers.get("content-type", "application/octet-stream"),
                                    size_bytes=len(raw_bytes),
                                    data=raw_bytes,
                                )
                                self._intercepted_resources.append(resource)
                                self._resource_event.set()
                                return
                except Exception as e:
                    logger.debug(f"No se pudo extraer URL del JSON de descarga: {e}")

            # Ignore fonts, images, and audio/video assets
            lower_url = url.lower().split("?")[0]
            if lower_url.endswith((".ttf", ".woff", ".woff2", ".otf", ".eot", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js", ".m3u8", ".ts")):
                return

            # Explicitly ignore preview PDFs (Wuolah truncates previews to 6 pages)
            if "preview.pdf" in lower_url or "/previews/" in lower_url:
                logger.debug(f"Descartando vista previa parcial de documento: {url[:80]}")
                return

            # Ignore tracking beacons and conversions
            if any(ad_d in lower_url for ad_d in ["googleadservices", "doubleclick", "analytics", "froged", "criteo", "pubmatic"]):
                return

            if is_pdf_content or is_pdf_extension or is_cdn_document:
                try:
                    data = await response.body()
                    if len(data) > 500:  # Ignore tiny tracking beacons or error responses
                        is_pdf_magic = data.startswith(b"%PDF")
                        is_xor_magic = len(data) >= 4 and bytes([b ^ 27 for b in data[:4]]) == b"%PDF"
                        
                        # Extract suggested filename
                        filename = None
                        if "filename=" in content_disp:
                            match = re.search(r'filename=["\']?([^"\';]+)["\']?', content_disp)
                            if match:
                                filename = match.group(1)

                        # Only accept if it actually exhibits PDF signature or Wuolah XOR obfuscation signature
                        if is_pdf_magic or is_xor_magic:
                            logger.info(f"Recurso de documento interceptado: {url[:80]} ({len(data)} bytes, tipo: {content_type})")
                            resource = DocumentResource(
                                url=url,
                                content_type=content_type,
                                size_bytes=len(data),
                                data=data,
                                filename=filename,
                            )
                            self._intercepted_resources.append(resource)
                            self._resource_event.set()
                except Exception as e:
                    logger.debug(f"Could not read response body for {url}: {e}")
        except Exception as e:
            logger.debug(f"Error analyzing network response: {e}")

    async def _on_download(self, download) -> None:
        """Capture Playwright download event."""
        try:
            logger.info(f"Evento de descarga disparado en navegador: {download.suggested_filename}")
            path = await download.path()
            if path:
                with open(path, "rb") as f:
                    data = f.read()
                resource = DocumentResource(
                    url=download.url,
                    content_type="application/pdf",
                    size_bytes=len(data),
                    data=data,
                    filename=download.suggested_filename,
                )
                if self._is_valid_complete_resource(resource):
                    self._intercepted_resources.append(resource)
                    self._resource_event.set()
        except Exception as e:
            logger.debug(f"Error handling download event: {e}")

    async def _inject_auth_cookies(self) -> None:
        """Inject authentication cookies into Chromium context if a session token is available."""
        if not self._context:
            return
        try:
            token = await self.get_auth_token()
            if not token:
                return

            user_id = None
            try:
                parts = token.split(".")
                if len(parts) >= 2:
                    padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
                    payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
                    if payload.get("id"):
                        user_id = str(payload["id"])
            except Exception:
                pass

            cookies_to_add = [
                {
                    "name": "token",
                    "value": token,
                    "domain": ".wuolah.com",
                    "path": "/",
                    "secure": True,
                    "sameSite": "Lax",
                },
                {
                    "name": "refreshToken",
                    "value": token,
                    "domain": ".wuolah.com",
                    "path": "/",
                    "secure": True,
                    "sameSite": "Lax",
                },
            ]
            if user_id:
                cookies_to_add.append({
                    "name": "user_id",
                    "value": user_id,
                    "domain": ".wuolah.com",
                    "path": "/",
                    "secure": True,
                    "sameSite": "Lax",
                })

            await self._context.add_cookies(cookies_to_add)
            logger.info(f"Cookies de sesión de Wuolah inyectadas en Chromium (user_id={user_id}).")
        except Exception as e:
            logger.debug(f"Error inyectando cookies de autenticación: {e}")

    async def fetch_document_metadata(self, file_id: int) -> dict:
        """Fetch official document metadata (e.g. numPages, name, size) from Wuolah API."""
        token = await self.get_auth_token()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            if self._page and not self._page.is_closed():
                resp = await self._page.request.get(f"https://api.wuolah.com/v2/documents/{file_id}", headers=headers)
                if resp.ok:
                    data = await resp.json()
                    logger.info(f"Metadatos oficiales obtenidos: '{data.get('name')}' ({data.get('numPages')} págs, {data.get('size')} bytes)")
                    return data
        except Exception as e:
            logger.debug(f"Error consultando metadatos via page request: {e}")

        try:
            req = urllib.request.Request(f"https://api.wuolah.com/v2/documents/{file_id}", headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    logger.info(f"Metadatos oficiales obtenidos (fallback): '{data.get('name')}' ({data.get('numPages')} págs)")
                    return data
        except Exception as e:
            logger.debug(f"Error consultando metadatos via urllib: {e}")

        return {}

    def _is_valid_complete_resource(self, resource: DocumentResource) -> bool:
        """Check if intercepted resource is a valid PDF and not an incomplete preview."""
        if not resource or not resource.data:
            return False

        # Ignore preview URLs and filenames
        if "preview" in resource.url.lower():
            return False
        if resource.filename and "preview" in resource.filename.lower():
            return False

        data = resource.data
        is_pdf_magic = data.startswith(b"%PDF")
        is_xor_magic = len(data) >= 4 and bytes([b ^ 27 for b in data[:4]]) == b"%PDF"
        if not (is_pdf_magic or is_xor_magic):
            return False

        # If expected_pages is known and > 6, verify page count
        if self._expected_pages and self._expected_pages > 6:
            try:
                pdf_data = data
                if is_xor_magic:
                    pdf_data = bytes([b ^ 27 for b in data[:4]]) + data[4:]
                reader = pypdf.PdfReader(io.BytesIO(pdf_data))
                page_count = len(reader.pages)
                if page_count <= 6 and self._expected_pages > 6:
                    logger.warning(
                        f"Recurso interceptado ({resource.url[:60]}) tiene {page_count} páginas, "
                        f"pero el documento oficial tiene {self._expected_pages}. Descartando por ser vista previa incompleta."
                    )
                    return False
            except Exception as e:
                logger.debug(f"No se pudo verificar páginas del recurso: {e}")

        return True

    async def open_login(self) -> None:
        """Open Wuolah login page in visible browser for interactive user login."""
        import sys
        import os

        # Check if running in a headless environment without an X server (such as a Docker container)
        is_headless_env = settings.BROWSER_HEADLESS or (sys.platform != "win32" and not os.environ.get("DISPLAY"))
        if is_headless_env:
            raise WuolahBrowserError(
                "Estás ejecutando la aplicación dentro de un contenedor Docker (sin entorno gráfico). "
                "Para iniciar sesión con Chromium la primera vez: para el contenedor en Docker Desktop, "
                "ejecuta 'python run.py' en tu ordenador para abrir la ventana de Chromium en tu pantalla, "
                "y una vez iniciada la sesión, vuelve a arrancar Docker Desktop."
            )

        if self._context is not None and self.headless:
            await self.close()

        self.headless = False
        await self.start()
        if not self._page:
            raise WuolahBrowserError("No se pudo iniciar la página del navegador.")
        logger.info("Abriendo https://wuolah.com/login para inicio de sesión interactivo...")
        await self._page.goto("https://wuolah.com/login", wait_until="domcontentloaded")
        await self._dismiss_cookie_banners()
        try:
            await self._page.bring_to_front()
        except Exception:
            pass

    async def clear_session(self) -> None:
        """Clear cookies and browser storage to allow switching or logging in with another account."""
        if self._context:
            try:
                await self._context.clear_cookies()
            except Exception as e:
                logger.debug(f"Error clearing cookies: {e}")
        if self._page and not self._page.is_closed():
            try:
                await self._page.evaluate("() => { try { localStorage.clear(); sessionStorage.clear(); } catch(e) {} }")
            except Exception as e:
                logger.debug(f"Error clearing storage: {e}")
        token_file = settings.temp_path / "browser_profile" / "session_token.txt"
        if token_file.exists():
            try:
                token_file.unlink()
            except Exception:
                pass
        settings.WUOLAH_TOKEN = None

    async def get_auth_token(self) -> Optional[str]:
        """
        Extract active JWT authentication token dynamically from Chromium.
        Checks:
        1. Saved session_token.txt file
        2. settings.WUOLAH_TOKEN (manual override if configured)
        3. Chromium cookies (across Wuolah domains)
        4. Chromium page localStorage and sessionStorage scanning for valid JWT signatures (eyJ...).
        """
        token_file = settings.temp_path / "browser_profile" / "session_token.txt"
        if token_file.exists():
            try:
                saved = token_file.read_text(encoding="utf-8").strip()
                if saved and len(saved) > 20:
                    return saved
            except Exception:
                pass

        if settings.WUOLAH_TOKEN:
            return settings.WUOLAH_TOKEN

        # 1. Search in Chromium cookies
        if self._context:
            try:
                cookies = await self._context.cookies()
                for c in cookies:
                    val = c.get("value", "")
                    name = c.get("name", "").lower()
                    if val.startswith("eyJ") and val.count(".") >= 2:
                        return val
                    if name in ("token", "jwt", "access_token", "auth_token") and val:
                        return val
            except Exception as e:
                logger.debug(f"Error checking cookies for token: {e}")

        # 2. Search in Chromium localStorage & sessionStorage
        if self._page and not self._page.is_closed():
            try:
                token = await self._page.evaluate("""() => {
                    const jwtRegex = /eyJ[A-Za-z0-9_-]{10,}\\.eyJ[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]+/;
                    try {
                        for (let i = 0; i < localStorage.length; i++) {
                            const k = localStorage.key(i);
                            const val = localStorage.getItem(k);
                            if (!val) continue;
                            const m = val.match(jwtRegex);
                            if (m) return m[0];
                        }
                    } catch(e) {}
                    try {
                        for (let i = 0; i < sessionStorage.length; i++) {
                            const k = sessionStorage.key(i);
                            const val = sessionStorage.getItem(k);
                            if (!val) continue;
                            const m = val.match(jwtRegex);
                            if (m) return m[0];
                        }
                    } catch(e) {}
                    return null;
                }""")
                if token:
                    return token
            except Exception as e:
                logger.debug(f"Error checking localStorage for token: {e}")

        return None

    async def is_authenticated(self) -> bool:
        """Check if user currently has an active session in Wuolah via cookies, localStorage, or Chromium profile."""
        if settings.WUOLAH_TOKEN:
            return True
        if not self._context:
            return False

        # Fast check: active token in cookies or storage
        token = await self.get_auth_token()
        if token:
            return True

        try:
            cookies = await self._context.cookies()
            auth_cookie_names = ["token", "auth", "session", "user", "wuolah_session", "connect.sid", "jwt", "access_token"]
            for c in cookies:
                name_lower = c.get("name", "").lower()
                if any(target in name_lower for target in auth_cookie_names) and c.get("value"):
                    return True

            if self._page and not self._page.is_closed():
                # Check localStorage for auth tokens
                has_token = await self._page.evaluate("""() => {
                    try {
                        for (let i = 0; i < localStorage.length; i++) {
                            const k = localStorage.key(i).toLowerCase();
                            if (k.includes('token') || k.includes('auth') || k.includes('user')) {
                                const val = localStorage.getItem(localStorage.key(i));
                                if (val && val !== 'null' && val !== 'undefined') return true;
                            }
                        }
                    } catch(e) {}
                    return false;
                }""")
                if has_token:
                    return True
        except Exception:
            pass
        return False

    async def _dismiss_cookie_banners(self) -> None:
        """Dismiss common cookie banners if present."""
        if not self._page or self._page.is_closed():
            return
        cookie_selectors = [
            ".fc-consent-root button.fc-cta-consent",
            ".fc-consent-root .fc-primary-button",
            "button.fc-cta-consent",
            "#onetrust-accept-btn-handler",
            "button:has-text('Consentir')",
            "button:has-text('Aceptar todas')",
            "button:has-text('Aceptar todo')",
            "button:has-text('Aceptar y continuar')",
            "button:has-text('Acepto')",
            "button:has-text('Aceptar')",
            "[aria-label*='Aceptar']",
            "[aria-label*='Consentir']",
        ]
        for sel in cookie_selectors:
            try:
                btn = await self._page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click(timeout=2000)
                    await asyncio.sleep(0.5)
                    break
            except Exception:
                pass

    async def open_document(self, url: str) -> None:
        """Navigate to requested document URL after validating security constraints."""
        validated_url = validate_wuolah_url(url)
        self._current_doc_url = validated_url
        await self.start()
        if not self._page:
            raise WuolahBrowserError("El navegador no está listo.")

        self._intercepted_resources.clear()
        self._resource_event.clear()

        # Query official document metadata (numPages, name) ahead of time
        file_id = extract_wuolah_file_id(validated_url)
        if file_id:
            try:
                self._current_doc_metadata = await self.fetch_document_metadata(file_id)
                self._expected_pages = self._current_doc_metadata.get("numPages")
            except Exception as e:
                logger.debug(f"Error al obtener metadatos para file_id {file_id}: {e}")

        # Ensure active session cookies are injected before navigating
        await self._inject_auth_cookies()

        await self._page.goto(validated_url, wait_until="domcontentloaded", timeout=settings.BROWSER_TIMEOUT_SECONDS * 1000)
        await self._dismiss_cookie_banners()

    async def wait_for_document(self, timeout_ms: int = 15000) -> bool:
        """Wait for the document page elements to render."""
        if not self._page:
            return False
        try:
            await self._page.wait_for_load_state("networkidle", timeout=timeout_ms)
            return True
        except Exception:
            return False

    async def find_document_resource(self, timeout_seconds: Optional[int] = None) -> DocumentResource:
        """
        Locate and return the captured document resource from network traffic.
        Attempts instant authorized API download first (~1s); if not possible, falls back to DOM clicking.
        """
        timeout = timeout_seconds or settings.DOWNLOAD_TIMEOUT_SECONDS

        # Check if already intercepted a valid PDF
        for r in self._intercepted_resources:
            if self._is_valid_complete_resource(r):
                if not r.filename and self._current_doc_metadata.get("name"):
                    r.filename = self._current_doc_metadata.get("name")
                return r

        # Fast-Path: Try instant authorized API download without waiting for ad countdowns
        file_id = None
        if self._page and not self._page.is_closed():
            file_id = extract_wuolah_file_id(self._page.url)
        if not file_id and self._current_doc_url:
            file_id = extract_wuolah_file_id(self._current_doc_url)

        if file_id:
            logger.info(f"Iniciando descarga instantánea autorizada (Vía Rápida) para fileId={file_id}...")
            direct_resource = await self._download_direct_api(file_id)
            if direct_resource:
                logger.info(f"¡Vía Rápida exitosa! Recurso obtenido en ~1s: {direct_resource.filename} ({direct_resource.size_bytes} bytes)")
                self._intercepted_resources.append(direct_resource)
                return direct_resource
            logger.info("Vía Rápida no pudo completar la descarga directa, continuando con fallback DOM...")

        # Auto-close any subscription / upsell tabs that Wuolah might have opened
        if self._context:
            for p in list(self._context.pages):
                if "shop" in p.url.lower() or "suscripciones" in p.url.lower() or "upgrade" in p.url.lower():
                    try:
                        logger.info(f"Cerrando pestaña de suscripción/upsell: {p.url[:80]}")
                        await p.close()
                    except Exception:
                        pass

        # Bring document page to front
        if self._page and not self._page.is_closed():
            try:
                await self._page.bring_to_front()
            except Exception:
                pass

        # Dismiss cookies if still lingering
        await self._dismiss_cookie_banners()

        # If "No tienes coins" modal is present, dismiss it with Escape and close buttons
        if self._page and not self._page.is_closed():
            try:
                await self._page.keyboard.press("Escape")
                await self._page.evaluate("""() => {
                    const closeBtns = Array.from(document.querySelectorAll('button, div[role="button"], svg'));
                    for (const b of closeBtns) {
                        const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                        if (aria.includes('close') || aria.includes('cerrar')) {
                            b.click();
                            return;
                        }
                    }
                }""")
                await asyncio.sleep(0.5)
            except Exception:
                pass

        # Intelligent DOM-level button clicker: strictly target "con publi" and avoid "sin publi", coins, and Turbo
        if self._page and not self._page.is_closed():
            try:
                click_result = await self._page.evaluate("""() => {
                    const elements = Array.from(document.querySelectorAll('button, a, div[role="button"], [data-testid*="download"]'));
                    
                    // 1. First priority: Specifically "con publi" / "con publicidad" / "con anuncios" (0 coins)
                    for (const el of elements) {
                        const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                        // Strictly EXCLUDE paid options: "sin publi", coins, turbo, pro, suscripciones
                        if (txt.includes('sin publi') || txt.includes('sin publicidad') || txt.includes('sin anuncios') || 
                            txt.includes('turbo') || txt.includes('pro') || txt.includes('suscrip') || txt.includes('comprar') ||
                            (txt.includes('coin') && !txt.includes('0'))) {
                            continue;
                        }
                        if (txt.includes('con publi') || txt.includes('con publicidad') || txt.includes('con anuncios') || txt.includes('gratis')) {
                            el.click();
                            return { clicked: true, type: 'con_publi_free', text: txt };
                        }
                    }

                    // 2. Second priority: Any download button that explicitly is NOT "sin publi" or Turbo
                    for (const el of elements) {
                        const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                        if (txt.includes('sin publi') || txt.includes('sin publicidad') || txt.includes('sin anuncios') || 
                            txt.includes('turbo') || txt.includes('pro') || txt.includes('suscrip') || txt.includes('coin')) {
                            continue;
                        }
                        if (txt.includes('descargar') || txt.includes('descarga')) {
                            el.click();
                            return { clicked: true, type: 'general_free_download', text: txt };
                        }
                    }

                    return { clicked: false };
                }""")
                if click_result.get("clicked"):
                    logger.info(f"Clic realizado en Wuolah ({click_result.get('type')}): '{click_result.get('text')}'")
                    await asyncio.sleep(1.5)
            except Exception as e:
                logger.debug(f"Error en evaluación DOM de descarga: {e}")

            # If a confirmation modal opened, confirm free / ad download
            try:
                modal_click = await self._page.evaluate("""() => {
                    const modalButtons = Array.from(document.querySelectorAll('.modal button, [role="dialog"] button, button'));
                    for (const btn of modalButtons) {
                        const txt = (btn.innerText || btn.textContent || '').trim().toLowerCase();
                        if (txt.includes('sin publi') || txt.includes('sin publicidad') || txt.includes('turbo') || txt.includes('pro') || txt.includes('suscrip')) continue;
                        if (txt.includes('con publi') || txt.includes('con publicidad') || txt.includes('anuncio') || txt.includes('gratis') || txt.includes('continuar') || txt.includes('saltar')) {
                            btn.click();
                            return { clicked: true, text: txt };
                        }
                    }
                    return { clicked: false };
                }""")
                if modal_click.get("clicked"):
                    logger.info(f"Confirmación en modal realizada: '{modal_click.get('text')}'")
                    await asyncio.sleep(1.5)
            except Exception as e:
                logger.debug(f"Error confirmando modal de descarga: {e}")

        # Wait loop for network interception, handling any ad countdown or subsequent confirmation
        start_wait = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_wait < timeout:
            # If any new upsell tab opened during wait, close it and bring document page to front
            if self._context:
                for p in list(self._context.pages):
                    if "shop" in p.url.lower() or "suscripciones" in p.url.lower() or "upgrade" in p.url.lower():
                        try:
                            logger.info(f"Cerrando pestaña emergente de suscripción: {p.url[:80]}")
                            await p.close()
                        except Exception:
                            pass

            if self._intercepted_resources:
                for r in self._intercepted_resources:
                    if self._is_valid_complete_resource(r):
                        if not r.filename and self._current_doc_metadata.get("name"):
                            r.filename = self._current_doc_metadata.get("name")
                        return r

            # Check if an ad countdown finished and revealed a final download button
            if self._page and not self._page.is_closed():
                try:
                    await self._page.evaluate("""() => {
                        const elements = Array.from(document.querySelectorAll('.chakra-modal__content-container button, [role="dialog"] button, button, a'));
                        for (const el of elements) {
                            if (el.disabled || el.getAttribute('aria-disabled') === 'true') continue;
                            const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                            if (txt === 'descargar' || txt.includes('descargar ahora') || txt.includes('saltar y descargar') || txt.includes('descargar archivo')) {
                                el.click();
                                break;
                            }
                        }
                    }""")
                except Exception:
                    pass

                # If reCAPTCHA modal appears, attempt to click the anchor
                try:
                    for f in self._page.frames:
                        if "recaptcha" in f.url and "anchor" in f.url:
                            anchor = f.locator("#recaptcha-anchor")
                            if await anchor.count() > 0 and await anchor.is_visible():
                                await anchor.click(timeout=1000)
                                break
                except Exception:
                    pass

            await asyncio.sleep(1.0)

        if self._intercepted_resources:
            for r in self._intercepted_resources:
                if self._is_valid_complete_resource(r):
                    if not r.filename and self._current_doc_metadata.get("name"):
                        r.filename = self._current_doc_metadata.get("name")
                    return r

        if self._page and not self._page.is_closed():
            try:
                screenshot_path = settings.temp_path / "last_browser_state.png"
                await self._page.screenshot(path=str(screenshot_path))
                logger.info(f"Captura de estado del navegador guardada en: {screenshot_path}. URL actual: {self._page.url}")
            except Exception:
                pass

        raise WuolahBrowserError(
            "No se pudo localizar el recurso del documento en el tráfico de red tras el tiempo de espera. "
            "Asegúrate de que estás en la pestaña del documento y selecciona 'Descargar con publicidad'."
        )

    async def _download_direct_api(self, file_id: int) -> Optional[DocumentResource]:
        """
        Attempt to request the signed document URL directly via POST /v2/download
        using the active authenticated session from Chromium, avoiding frontend ad countdowns.
        """
        if not self._context or not self._page or self._page.is_closed():
            return None

        try:
            token = await self.get_auth_token()
            machine_id = "unknown"
            if self._context:
                cookies = await self._context.cookies()
                for c in cookies:
                    if c.get("name") == "segMachineId" and c.get("value"):
                        machine_id = c["value"]
                        break

            if not token:
                logger.info("No se encontró token JWT en Chromium para descarga directa por API. Continuando con fallback...")
                return None

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "Referer": "https://wuolah.com/",
                "x-seg-machine-id": machine_id,
            }
            payload = {
                "fileId": file_id,
                "adblockDetected": False,
                "noAdsWithCoins": False,
                "avoidFallback": True,
            }

            resp = await self._page.request.post(
                "https://api.wuolah.com/v2/download",
                data=json.dumps(payload),
                headers=headers,
                timeout=15000,
            )

            if resp.status != 200:
                logger.debug(f"API /v2/download respondió con status {resp.status}")
                return None

            data = await resp.json()
            download_url = data.get("url")
            if not download_url or not isinstance(download_url, str) or not download_url.startswith("http"):
                logger.debug("API /v2/download no devolvió una URL de descarga válida.")
                return None

            logger.info(f"URL firmada obtenida de API de Wuolah: {download_url[:70]}...")
            doc_resp = await self._page.request.get(download_url, timeout=30000)
            if not doc_resp.ok:
                logger.debug(f"Petición a URL firmada falló con status {doc_resp.status}")
                return None

            raw_bytes = await doc_resp.body()
            if len(raw_bytes) < 100:
                logger.debug(f"Respuesta de PDF demasiado pequeña ({len(raw_bytes)} bytes)")
                return None

            # Extract filename from Content-Disposition header if available
            disp = doc_resp.headers.get("content-disposition", "")
            filename = None
            if "filename=" in disp:
                match = re.search(r'filename=["\']?([^"\';]+)["\']?', disp)
                if match:
                    filename = match.group(1)

            if not filename and self._current_doc_metadata.get("name"):
                filename = self._current_doc_metadata.get("name")

            resource = DocumentResource(
                url=download_url,
                content_type=doc_resp.headers.get("content-type", "application/pdf"),
                size_bytes=len(raw_bytes),
                data=raw_bytes,
                filename=filename,
            )
            if self._is_valid_complete_resource(resource):
                return resource
            return None

        except Exception as e:
            logger.debug(f"Excepción durante descarga directa por API: {e}")
            return None

    async def close(self) -> None:
        """Close browser page, context, and Playwright session."""
        try:
            if self._page and not self._page.is_closed():
                await self._page.close()
        except Exception:
            pass
        try:
            if self._context:
                await self._context.close()
        except Exception:
            pass
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
        self._intercepted_resources.clear()
        self._resource_event.clear()

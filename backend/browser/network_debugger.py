import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Download, Page, Request, Response

logger = logging.getLogger("wuolah.debugger")

SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-auth-token",
    "x-amz-security-token",
    "x-xsrf-token",
}


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Remove sensitive authentication tokens and cookies from headers."""
    clean = {}
    for k, v in headers.items():
        k_lower = k.lower()
        if k_lower in SENSITIVE_HEADERS or any(s in k_lower for s in ["token", "secret", "cookie", "auth"]):
            clean[k] = "[REDACTED_SENSITIVE_DATA]"
        else:
            clean[k] = v
    return clean


def safe_json_structure(data: Any, max_depth: int = 4) -> Any:
    """Safely extract the schema / keys of a JSON object without revealing private values."""
    if max_depth <= 0:
        return "[DEPTH_LIMIT]"

    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in ["token", "secret", "password", "hash", "key"]):
                result[k] = f"[TOKEN_STRING len={len(str(v))}]" if isinstance(v, str) else "[REDACTED]"
            elif isinstance(v, (dict, list)):
                result[k] = safe_json_structure(v, max_depth - 1)
            elif isinstance(v, str) and (v.startswith("http://") or v.startswith("https://")):
                # URLs are crucial for network debugging; sanitize query params if tokens
                parsed = urlparse(v)
                result[k] = f"{parsed.scheme}://{parsed.netloc}{parsed.path}" + ("?...[PARAMS]" if parsed.query else "")
            elif isinstance(v, (int, float, bool)) or v is None:
                result[k] = v
            else:
                result[k] = f"[{type(v).__name__}]"
        return result
    elif isinstance(data, list):
        if not data:
            return []
        return [safe_json_structure(data[0], max_depth - 1)]
    return f"[{type(data).__name__}]"


class NetworkDebugger:
    """
    Non-intrusive network debugger for observing and auditing
    Wuolah HTTP requests, responses, redirects, and download events.
    """

    def __init__(self, name: str = "trace"):
        self.name = name
        self.events: List[Dict[str, Any]] = []
        self.downloads: List[Dict[str, Any]] = []
        self.new_pages: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    def attach_to_context(self, context: BrowserContext) -> None:
        """Attach listeners to context for tracking tabs and network across all pages."""
        context.on("page", self._on_new_page)
        for page in context.pages:
            self.attach_to_page(page)

    def attach_to_page(self, page: Page) -> None:
        """Attach request, response, failed, and download listeners to a specific page."""
        page.on("request", self._on_request)
        page.on("response", self._on_response)
        page.on("requestfailed", self._on_request_failed)
        page.on("download", self._on_download)

    def _on_new_page(self, page: Page) -> None:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "new_page_opened",
            "url": page.url,
        }
        self.new_pages.append(event)
        logger.info(f"[Debugger] Nueva pestaña detectada: {page.url}")
        self.attach_to_page(page)

    def _on_request(self, request: Request) -> None:
        try:
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "request",
                "request_id": id(request),
                "page_url": request.frame.page.url if request.frame and request.frame.page else "unknown",
                "method": request.method,
                "url": request.url,
                "resource_type": request.resource_type,
                "headers": sanitize_headers(request.headers),
                "is_navigation": request.is_navigation_request(),
            }

            # Safe post data inspection
            try:
                post_data = request.post_data
                if post_data:
                    try:
                        parsed_json = json.loads(post_data)
                        event["post_data_schema"] = safe_json_structure(parsed_json)
                    except Exception:
                        event["post_data_sample"] = f"[TEXT len={len(post_data)}]"
            except Exception:
                event["post_data_sample"] = "[BINARY_OR_COMPRESSED_DATA]"

            self.events.append(event)
        except Exception as e:
            logger.debug(f"Error handling request event: {e}")

    async def _on_response(self, response: Response) -> None:
        req = response.request
        status = response.status
        url = response.url
        headers = response.headers
        content_type = headers.get("content-type", "")

        event: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "response",
            "request_id": id(req),
            "method": req.method,
            "url": url,
            "status": status,
            "status_text": response.status_text,
            "resource_type": req.resource_type,
            "content_type": content_type,
            "content_disposition": headers.get("content-disposition"),
            "headers": sanitize_headers(headers),
            "redirect_chain": [],
        }

        # Trace redirect chains (301, 302, 303, 307, 308)
        redirect_from = req.redirected_from
        while redirect_from:
            event["redirect_chain"].append({
                "url": redirect_from.url,
                "method": redirect_from.method,
            })
            redirect_from = redirect_from.redirected_from

        # Analyze JSON responses safely
        if "application/json" in content_type:
            try:
                body = await response.json()
                event["json_structure"] = safe_json_structure(body)
                if isinstance(body, dict):
                    event["json_keys"] = list(body.keys())
            except Exception:
                pass

        # Flag binary / PDF documents
        is_pdf = "application/pdf" in content_type or url.lower().split("?")[0].endswith(".pdf")
        is_binary = "application/octet-stream" in content_type
        event["is_pdf"] = is_pdf
        event["is_binary"] = is_binary

        if is_pdf or is_binary:
            try:
                body_bytes = await response.body()
                event["size_bytes"] = len(body_bytes)
                event["starts_with_pdf"] = body_bytes.startswith(b"%PDF")
                event["starts_with_xor27"] = (
                    len(body_bytes) >= 4 and bytes([b ^ 27 for b in body_bytes[:4]]) == b"%PDF"
                )
            except Exception:
                event["size_bytes"] = headers.get("content-length")

        self.events.append(event)

    def _on_request_failed(self, request: Request) -> None:
        failure = request.failure
        self.events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "request_failed",
            "request_id": id(request),
            "method": request.method,
            "url": request.url,
            "resource_type": request.resource_type,
            "error_text": failure if failure else "Unknown failure",
        })

    def _on_download(self, download: Download) -> None:
        info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "download",
            "url": download.url,
            "suggested_filename": download.suggested_filename,
        }
        self.downloads.append(info)
        self.events.append(info)
        logger.info(f"[Debugger] DOWNLOAD detectado: {download.suggested_filename} ({download.url})")

    def export_trace_json(self, output_path: Path) -> None:
        """Export raw trace events to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "session_name": self.name,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_events": len(self.events),
            "downloads_count": len(self.downloads),
            "new_pages_count": len(self.new_pages),
            "downloads": self.downloads,
            "new_pages": self.new_pages,
            "events": self.events,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def export_summary_text(self, output_path: Path) -> None:
        """Export human-readable network summary formatted as requested."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"=== NETWORK TRACE: {self.name.upper()} ===",
            f"Total events recorded: {len(self.events)}",
            f"Downloads triggered: {len(self.downloads)}",
            f"New tabs/pages opened: {len(self.new_pages)}",
            "",
        ]

        counter = 1
        for ev in self.events:
            ev_type = ev.get("event_type")
            if ev_type == "response":
                url = ev.get("url", "")
                method = ev.get("method", "GET")
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
                    lines.append(f"    is_pdf=True | size={ev.get('size_bytes')} | pdf_magic={ev.get('starts_with_pdf')}")

                if ev.get("is_binary"):
                    lines.append(f"    is_binary=True | size={ev.get('size_bytes')} | xor27_magic={ev.get('starts_with_xor27')}")

                lines.append("")
                counter += 1

            elif ev_type == "download":
                lines.append(f"[{counter}] DOWNLOAD")
                lines.append(f"    url={ev.get('url')}")
                lines.append(f"    suggested_filename={ev.get('suggested_filename')}")
                lines.append("")
                counter += 1

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

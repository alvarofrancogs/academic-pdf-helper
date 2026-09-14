import ipaddress
import re
from urllib.parse import urlparse
from backend.core.config import settings


class SecurityError(Exception):
    """Raised when a security validation fails."""
    pass


def is_private_or_loopback_host(hostname: str) -> bool:
    """Check if a hostname resolves to or is a private/loopback IP address."""
    if not hostname:
        return True
    
    clean_host = hostname.strip().lower()
    if clean_host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
        
    try:
        ip = ipaddress.ip_address(clean_host)
        return ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local
    except ValueError:
        # Not an IP literal, domain name check
        return False


def validate_wuolah_url(url: str) -> str:
    """
    Strict validation of Wuolah URLs to prevent SSRF and arbitrary resource access.
    Only HTTPS and allowed Wuolah domains are permitted.
    """
    if not url or not isinstance(url, str):
        raise SecurityError("URL no proporcionada o formato inválido.")

    clean_url = url.strip()
    
    # Check for dangerous schemes
    if clean_url.lower().startswith(("javascript:", "file:", "data:", "ftp:", "gopher:", "vbscript:")):
        raise SecurityError("Esquema de URL no permitido.")

    parsed = urlparse(clean_url)

    if parsed.scheme.lower() not in ("https",):
        raise SecurityError("Solo se permiten URLs seguras con protocolo HTTPS.")

    hostname = parsed.hostname
    if not hostname:
        raise SecurityError("Host no válido en la URL.")

    # Prevent loopback or private hostnames
    if is_private_or_loopback_host(hostname):
        raise SecurityError("Acceso a direcciones locales o privadas bloqueado (SSRF).")

    # Domain whitelist check
    allowed_domains = [d.lower() for d in settings.ALLOWED_DOMAINS]
    host_lower = hostname.lower()
    
    is_allowed = False
    for allowed in allowed_domains:
        if host_lower == allowed or host_lower.endswith("." + allowed):
            is_allowed = True
            break

    if not is_allowed:
        raise SecurityError(f"Dominio no permitido: '{hostname}'. Solo se permite wuolah.com.")

    # Check path length and dangerous characters
    if ".." in parsed.path or "\x00" in clean_url:
        raise SecurityError("Path traversal o caracteres nulos detectados en la URL.")

    return clean_url


def sanitize_filename(name: str | None, default: str = "documento_wuolah.pdf") -> str:
    """
    Sanitize an untrusted filename, stripping directory traversal characters
    and keeping only safe alphanumeric characters, dashes, underscores, and dots.
    """
    if not name or not isinstance(name, str):
        return default

    # Remove paths
    clean = name.replace("\\", "/").split("/")[-1].strip()
    # Remove dangerous characters
    clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', clean)
    # Ensure not empty and ends with .pdf
    if not clean or clean in (".", ".."):
        return default
        
    if not clean.lower().endswith(".pdf"):
        clean = f"{clean}.pdf"

    return clean


def extract_wuolah_file_id(url: str) -> int | None:
    """
    Extract the numeric document fileId from a Wuolah URL.
    Supports formats like:
      - /apuntes/.../titulo-pdf-14080870
      - /document/14080870
      - /file/14080870
    """
    if not url or not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url.strip())
        path = parsed.path.rstrip("/")
        if not path:
            return None
        last_segment = path.split("/")[-1]
        
        # Match -<id> at the end of slug, e.g. "preguntas-examen-ssoo-i-pdf-14080870"
        match = re.search(r'-(\d+)$', last_segment)
        if match:
            return int(match.group(1))
            
        # Match direct numeric segment, e.g. "/document/14080870"
        if last_segment.isdigit():
            return int(last_segment)
            
        # Fallback regex for any trailing digits in last segment
        match_any = re.search(r'(\d+)$', last_segment)
        if match_any:
            return int(match_any.group(1))
    except Exception:
        pass
    return None


import pytest
from backend.core.security import (
    validate_wuolah_url,
    sanitize_filename,
    SecurityError,
    is_private_or_loopback_host,
)


def test_valid_wuolah_urls():
    valid_urls = [
        "https://wuolah.com/apuntes/universidad-de-sevilla/ingenieria-informatica/calculo-12345",
        "https://www.wuolah.com/documents/matematicas-tema-1-pdf",
        "https://wuolah.com/explore/document/abc-def-ghi?page=1",
    ]
    for url in valid_urls:
        assert validate_wuolah_url(url) == url


def test_invalid_schemes():
    invalid_urls = [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "file:///C:/Windows/System32/drivers/etc/hosts",
        "ftp://wuolah.com/document.pdf",
        "data:text/html,<script>alert(1)</script>",
    ]
    for url in invalid_urls:
        with pytest.raises(SecurityError):
            validate_wuolah_url(url)


def test_ssrf_and_private_addresses():
    blocked_hosts = [
        "http://localhost",
        "https://localhost/doc",
        "https://127.0.0.1/doc",
        "https://127.0.0.1:8000/doc",
        "https://10.0.0.1/doc",
        "https://192.168.1.1/doc",
        "https://172.16.0.1/doc",
        "https://0.0.0.0/doc",
    ]
    for url in blocked_hosts:
        with pytest.raises(SecurityError):
            validate_wuolah_url(url)


def test_disallowed_external_domains():
    disallowed_urls = [
        "https://google.com/malicious.pdf",
        "https://fake-wuolah.com/download",
        "https://wuolah.com.attacker.com/doc",
        "https://evil.org/wuolah.com",
    ]
    for url in disallowed_urls:
        with pytest.raises(SecurityError):
            validate_wuolah_url(url)


def test_is_private_or_loopback_host():
    assert is_private_or_loopback_host("localhost") is True
    assert is_private_or_loopback_host("127.0.0.1") is True
    assert is_private_or_loopback_host("192.168.1.50") is True
    assert is_private_or_loopback_host("10.0.0.100") is True
    assert is_private_or_loopback_host("wuolah.com") is False
    assert is_private_or_loopback_host("www.wuolah.com") is False


def test_sanitize_filename():
    assert sanitize_filename("apuntes_tema1.pdf") == "apuntes_tema1.pdf"
    assert sanitize_filename("../../etc/passwd") == "passwd.pdf"
    assert sanitize_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe.pdf"
    assert sanitize_filename("Tema 1: Métodos Numéricos?.pdf") == "Tema_1__M_todos_Num_ricos_.pdf"
    assert sanitize_filename(None) == "documento_wuolah.pdf"
    assert sanitize_filename("") == "documento_wuolah.pdf"
    assert sanitize_filename("   ") == "documento_wuolah.pdf"
    assert sanitize_filename("valid_doc") == "valid_doc.pdf"

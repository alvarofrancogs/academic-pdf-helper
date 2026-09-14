import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core.security import extract_wuolah_file_id
from backend.browser.wuolah import WuolahBrowser
from backend.browser.resource import DocumentResource


def test_extract_wuolah_file_id_standard_url():
    url = "https://wuolah.com/apuntes/sistemas-operativos-i/preguntas-examen-ssoo-i-pdf-14080870"
    assert extract_wuolah_file_id(url) == 14080870


def test_extract_wuolah_file_id_with_query_and_fragment():
    url = "https://wuolah.com/apuntes/sistemas-operativos-i/preguntas-examen-ssoo-i-pdf-14080870?utm_source=wuolah&ref=1#page=2"
    assert extract_wuolah_file_id(url) == 14080870


def test_extract_wuolah_file_id_document_path():
    url = "https://wuolah.com/document/3441252/"
    assert extract_wuolah_file_id(url) == 3441252


def test_extract_wuolah_file_id_simple_slug():
    url = "https://wuolah.com/apuntes/matematicas/algebra-3441228"
    assert extract_wuolah_file_id(url) == 3441228


def test_extract_wuolah_file_id_invalid_or_missing():
    assert extract_wuolah_file_id("") is None
    assert extract_wuolah_file_id(None) is None  # type: ignore
    assert extract_wuolah_file_id("https://wuolah.com/apuntes/sistemas-operativos-i/") is None
    assert extract_wuolah_file_id("https://wuolah.com/login") is None


@pytest.mark.asyncio
async def test_download_direct_api_success():
    browser = WuolahBrowser(headless=True)
    browser._context = MagicMock()
    browser._page = MagicMock()
    browser._page.is_closed.return_value = False

    # Mock cookies
    browser._context.cookies = AsyncMock(return_value=[
        {"name": "token", "value": "mock_jwt_token_123"},
        {"name": "segMachineId", "value": "mock_machine_id_456"}
    ])

    # Mock POST /v2/download response
    mock_post_resp = MagicMock()
    mock_post_resp.status = 200
    mock_post_resp.json = AsyncMock(return_value={
        "downloadId": "dl-123",
        "url": "https://api.wuolah.com/media/docs-pdf/tmp/14080870.pdf?Signature=abc",
        "isEncrypted": False,
        "extension": "pdf"
    })

    # Mock GET signed URL response
    mock_get_resp = MagicMock()
    mock_get_resp.ok = True
    mock_get_resp.status = 200
    mock_get_resp.headers = {
        "content-type": "application/pdf",
        "content-disposition": 'attachment; filename="documento_examen.pdf"'
    }
    mock_get_resp.body = AsyncMock(return_value=b"%PDF-1.7 mock valid content" + b"x" * 200)

    browser._page.request = MagicMock()
    browser._page.request.post = AsyncMock(return_value=mock_post_resp)
    browser._page.request.get = AsyncMock(return_value=mock_get_resp)

    resource = await browser._download_direct_api(14080870)

    assert resource is not None
    assert isinstance(resource, DocumentResource)
    assert resource.size_bytes > 200
    assert resource.filename == "documento_examen.pdf"
    assert resource.data.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_download_direct_api_missing_token_returns_none():
    browser = WuolahBrowser(headless=True)
    browser._context = MagicMock()
    browser._page = MagicMock()
    browser._page.is_closed.return_value = False

    # No token cookie
    browser._context.cookies = AsyncMock(return_value=[
        {"name": "unrelated_cookie", "value": "123"}
    ])

    resource = await browser._download_direct_api(14080870)
    assert resource is None


@pytest.mark.asyncio
async def test_download_direct_api_http_error_returns_none():
    browser = WuolahBrowser(headless=True)
    browser._context = MagicMock()
    browser._page = MagicMock()
    browser._page.is_closed.return_value = False

    browser._context.cookies = AsyncMock(return_value=[
        {"name": "token", "value": "mock_jwt_token_123"}
    ])

    mock_post_resp = MagicMock()
    mock_post_resp.status = 401
    browser._page.request = MagicMock()
    browser._page.request.post = AsyncMock(return_value=mock_post_resp)

    resource = await browser._download_direct_api(14080870)
    assert resource is None


@pytest.mark.asyncio
async def test_get_auth_token_from_local_storage():
    browser = WuolahBrowser(headless=True)
    browser._context = MagicMock()
    browser._page = MagicMock()
    browser._page.is_closed.return_value = False
    browser._context.cookies = AsyncMock(return_value=[])

    jwt_token = "eyJhbGciOiJSUzI1NiJ9.eyJpZCI6MTIzfQ.signature123"
    browser._page.evaluate = AsyncMock(return_value=jwt_token)

    token = await browser.get_auth_token()
    assert token == jwt_token

    is_auth = await browser.is_authenticated()
    assert is_auth is True


@pytest.mark.asyncio
async def test_get_auth_token_from_cookies():
    browser = WuolahBrowser(headless=True)
    browser._context = MagicMock()
    browser._page = MagicMock()
    browser._page.is_closed.return_value = False

    jwt_token = "eyJhbGciOiJSUzI1NiJ9.eyJpZCI6MTIzfQ.signature123"
    browser._context.cookies = AsyncMock(return_value=[
        {"name": "access_token", "value": jwt_token, "domain": ".wuolah.com"}
    ])

    token = await browser.get_auth_token()
    assert token == jwt_token

    is_auth = await browser.is_authenticated()
    assert is_auth is True

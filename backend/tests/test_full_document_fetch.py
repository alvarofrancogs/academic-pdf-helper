import asyncio
import io
from unittest.mock import AsyncMock, MagicMock, patch
import pypdf
import pytest

from backend.browser.resource import DocumentResource
from backend.browser.wuolah import WuolahBrowser


def create_dummy_pdf(num_pages: int) -> bytes:
    writer = pypdf.PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_is_valid_complete_resource_discards_preview_url():
    browser = WuolahBrowser(headless=True)
    pdf_bytes = create_dummy_pdf(6)
    
    # 1. URL with preview.pdf
    res_preview = DocumentResource(
        url="https://cdn.wuolahstatic.com/api/previews/document/123/v1-0/preview.pdf",
        content_type="application/pdf",
        size_bytes=len(pdf_bytes),
        data=pdf_bytes,
    )
    assert not browser._is_valid_complete_resource(res_preview)


@pytest.mark.asyncio
async def test_is_valid_complete_resource_discards_incomplete_pages():
    browser = WuolahBrowser(headless=True)
    browser._expected_pages = 48
    
    # Dummy 6-page PDF (preview)
    pdf_6_pages = create_dummy_pdf(6)
    res_6 = DocumentResource(
        url="https://cdn.wuolahservices.com/uploads/doc.pdf",
        content_type="application/pdf",
        size_bytes=len(pdf_6_pages),
        data=pdf_6_pages,
    )
    # Should be discarded because expected_pages is 48 but resource only has 6 pages
    assert not browser._is_valid_complete_resource(res_6)


@pytest.mark.asyncio
async def test_is_valid_complete_resource_accepts_complete_pages():
    browser = WuolahBrowser(headless=True)
    browser._expected_pages = 48
    
    # Dummy 48-page PDF
    pdf_48_pages = create_dummy_pdf(48)
    res_48 = DocumentResource(
        url="https://cdn.wuolahservices.com/uploads/doc_full.pdf",
        content_type="application/pdf",
        size_bytes=len(pdf_48_pages),
        data=pdf_48_pages,
        filename="teoria_completa.pdf",
    )
    assert browser._is_valid_complete_resource(res_48)


@pytest.mark.asyncio
async def test_is_valid_complete_resource_allows_small_documents():
    browser = WuolahBrowser(headless=True)
    browser._expected_pages = 3
    
    # Small 3-page document
    pdf_3_pages = create_dummy_pdf(3)
    res_3 = DocumentResource(
        url="https://cdn.wuolahservices.com/uploads/doc_short.pdf",
        content_type="application/pdf",
        size_bytes=len(pdf_3_pages),
        data=pdf_3_pages,
    )
    assert browser._is_valid_complete_resource(res_3)


@pytest.mark.asyncio
async def test_inject_auth_cookies():
    browser = WuolahBrowser(headless=True)
    # Fake JWT with id=4427149
    # Payload: {"id": 4427149, "email": "test@example.com"}
    fake_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJpZCI6NDQyNzE0OSwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIn0.signature"
    
    mock_context = MagicMock()
    mock_context.add_cookies = AsyncMock()
    browser._context = mock_context
    
    with patch.object(browser, "get_auth_token", AsyncMock(return_value=fake_jwt)):
        await browser._inject_auth_cookies()
        
    assert mock_context.add_cookies.called
    added = mock_context.add_cookies.call_args[0][0]
    names = [c["name"] for c in added]
    values = {c["name"]: c["value"] for c in added}
    
    assert "token" in names
    assert "refreshToken" in names
    assert "user_id" in names
    assert values["user_id"] == "4427149"
    assert values["token"] == fake_jwt

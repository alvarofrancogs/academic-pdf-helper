from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.browser.resource import DocumentResource
from backend.core.config import settings
from backend.jobs.manager import job_manager
from backend.main import app

client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "project" in data


def test_session_status():
    response = client.get("/api/session/status")
    assert response.status_code == 200
    data = response.json()
    assert "authenticated" in data
    assert "browser_running" in data


def test_process_invalid_url():
    response = client.post("/api/document/process", json={"url": "javascript:alert(1)"})
    assert response.status_code == 400
    assert "no permitido" in response.json()["detail"].lower()

    response_evil = client.post("/api/document/process", json={"url": "https://attacker.com/doc"})
    assert response_evil.status_code == 400


def test_process_valid_url_queues_job():
    with patch.object(job_manager, "run_document_pipeline", new=AsyncMock()):
        response = client.post(
            "/api/document/process",
            json={"url": "https://wuolah.com/document/calculo-tema1-12345"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"

        job_id = data["job_id"]
        status_resp = client.get(f"/api/document/status/{job_id}")
        assert status_resp.status_code == 200
        assert status_resp.json()["job_id"] == job_id


def test_status_nonexistent_job():
    response = client.get("/api/document/status/nonexistent123")
    assert response.status_code == 404


def test_download_not_ready():
    with patch.object(job_manager, "run_document_pipeline", new=AsyncMock()):
        response = client.post(
            "/api/document/process",
            json={"url": "https://wuolah.com/document/test-doc"},
        )
        job_id = response.json()["job_id"]
        download_resp = client.get(f"/api/document/download/{job_id}")
        assert download_resp.status_code == 400


@pytest.mark.asyncio
async def test_end_to_end_job_execution_with_obfuscated_wuolah_resource(sample_obfuscated_pdf, sample_valid_pdf):
    """
    Test complete job workflow from creation to ready status and file download,
    simulating browser network interception of an obfuscated Wuolah PDF.
    """
    mock_browser = AsyncMock()
    mock_browser.start = AsyncMock()
    mock_browser.is_authenticated = AsyncMock(return_value=True)
    mock_browser.open_document = AsyncMock()
    mock_browser.wait_for_document = AsyncMock(return_value=True)
    mock_browser.find_document_resource = AsyncMock(
        return_value=DocumentResource(
            url="https://cdn.wuolah.com/documents/apuntes_calculo_28pag.pdf",
            content_type="application/octet-stream",
            size_bytes=len(sample_obfuscated_pdf),
            data=sample_obfuscated_pdf,
            filename="apuntes_calculo_28pag.pdf",
        )
    )

    # 1. Create Job
    job = await job_manager.create_job("https://wuolah.com/documents/apuntes_calculo_28pag")
    job_id = job["job_id"]

    # 2. Run pipeline
    await job_manager.run_document_pipeline(
        job_id=job_id,
        url="https://wuolah.com/documents/apuntes_calculo_28pag",
        browser=mock_browser,
    )

    # 3. Check Job Status
    updated_job = await job_manager.get_job(job_id)
    assert updated_job["status"] == "ready"
    assert updated_job["progress"] == 100
    assert updated_job["result_metadata"]["pages"] == 28
    assert updated_job["result_metadata"]["detected_type"] == "wuolah_xor_obfuscated"

    # 4. Download document via API
    download_resp = client.get(f"/api/document/download/{job_id}")
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    assert download_resp.content == sample_valid_pdf


def test_set_session_token_success():
    resp = client.post("/api/session/token", json={"token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.valid_test_token"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["authenticated"] is True
    token_file = settings.temp_path / "browser_profile" / "session_token.txt"
    if token_file.exists():
        token_file.unlink()
    settings.WUOLAH_TOKEN = None


def test_set_session_token_invalid():
    resp = client.post("/api/session/token", json={"token": "short"})
    assert resp.status_code == 400


def test_clear_session():
    resp = client.post("/api/session/clear")
    assert resp.status_code == 200
    data = resp.json()
    assert data["authenticated"] is False

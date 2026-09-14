import asyncio
import os
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse

from backend.api.schemas import (
    HealthResponse,
    JobStatusResponse,
    ProcessDocumentRequest,
    ProcessDocumentResponse,
    SessionStatusResponse,
    SessionTokenRequest,
)
from backend.browser.wuolah import WuolahBrowser
from backend.core.config import settings
from backend.core.security import validate_wuolah_url, SecurityError
from backend.jobs.manager import job_manager

router = APIRouter()

# Shared browser instance for interactive login and session reuse
_browser_instance: WuolahBrowser | None = None


def get_browser() -> WuolahBrowser:
    global _browser_instance
    if _browser_instance is None:
        _browser_instance = WuolahBrowser()
    return _browser_instance


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Service health check endpoint."""
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        project=settings.PROJECT_NAME,
    )


@router.get("/session/status", response_model=SessionStatusResponse)
async def get_session_status():
    """Check whether the browser is running and if the user has an active session."""
    browser = get_browser()
    browser_running = (browser._context is not None) or (browser._browser is not None and browser._browser.is_connected())
    is_auth = await browser.is_authenticated()

    return SessionStatusResponse(
        authenticated=is_auth,
        browser_running=browser_running,
        message="Sesión iniciada en Wuolah" if is_auth else "Sesión no detectada",
    )


@router.post("/session/start", response_model=SessionStatusResponse)
async def start_session():
    """
    Launch Chromium in visible mode and navigate to Wuolah so the user can log in directly.
    No credentials, cookies, or tokens are logged or stored.
    """
    browser = get_browser()
    try:
        await browser.open_login()
        is_auth = await browser.is_authenticated()
        return SessionStatusResponse(
            authenticated=is_auth,
            browser_running=True,
            message="Navegador abierto. Inicia sesión en Wuolah en la ventana que ha aparecido.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando navegador para inicio de sesión: {str(e)}",
        )


@router.post("/session/switch", response_model=SessionStatusResponse)
async def switch_session():
    """
    Clear current session cookies and open Wuolah login to switch or renew account.
    """
    browser = get_browser()
    try:
        await browser.clear_session()
        await browser.open_login()
        is_auth = await browser.is_authenticated()
        return SessionStatusResponse(
            authenticated=is_auth,
            browser_running=True,
            message="Sesión anterior limpiada. Inicia sesión con tu nueva cuenta en la ventana.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cambiar sesión: {str(e)}",
        )


@router.post("/session/token", response_model=SessionStatusResponse)
async def set_session_token(request: SessionTokenRequest):
    """
    Save an active authentication token directly from the web UI or bookmarklet without opening Chromium GUI.
    """
    token = request.token.strip()
    if not token or len(token) < 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido. Debe ser un token JWT válido de Wuolah.",
        )
    profile_dir = settings.temp_path / "browser_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    token_file = profile_dir / "session_token.txt"
    token_file.write_text(token, encoding="utf-8")
    settings.WUOLAH_TOKEN = token

    return SessionStatusResponse(
        authenticated=True,
        browser_running=True,
        message="¡Sesión vinculada con éxito!",
    )


@router.post("/session/clear", response_model=SessionStatusResponse)
async def clear_session():
    """
    Clear saved session token and browser cookies cleanly.
    """
    browser = get_browser()
    await browser.clear_session()
    return SessionStatusResponse(
        authenticated=False,
        browser_running=False,
        message="Sesión cerrada correctamente.",
    )


@router.post("/document/process", response_model=ProcessDocumentResponse)
async def process_document(request: ProcessDocumentRequest, background_tasks: BackgroundTasks):
    """
    Validate URL and schedule document extraction and PDF pipeline processing.
    """
    try:
        validated_url = validate_wuolah_url(request.url)
    except SecurityError as se:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(se),
        )

    # Clean up expired jobs
    await job_manager.cleanup_expired_jobs()

    # Create job
    job = await job_manager.create_job(validated_url)
    job_id = job["job_id"]

    # Launch processing in background
    browser = get_browser()
    background_tasks.add_task(
        job_manager.run_document_pipeline,
        job_id=job_id,
        url=validated_url,
        browser=browser,
    )

    return ProcessDocumentResponse(
        job_id=job_id,
        status=job["status"],
    )


@router.get("/document/status/{job_id}", response_model=JobStatusResponse)
async def get_document_status(job_id: str):
    """Retrieve current processing status and metadata for a job."""
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trabajo '{job_id}' no encontrado o expirado.",
        )

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job["progress"],
        message=job["message"],
        filename=job.get("filename"),
        result_metadata=job.get("result_metadata"),
        error=job.get("error"),
    )


@router.get("/document/download/{job_id}")
async def download_document(job_id: str, inline: bool = False):
    """Download or preview the finalized, validated PDF file."""
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trabajo '{job_id}' no encontrado.",
        )

    if job["status"] != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo todavía no está listo para su descarga.",
        )

    result_path = job.get("result_path")
    if not result_path or not os.path.exists(result_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El archivo resultante no se encuentra disponible en el almacenamiento temporal.",
        )

    filename = job.get("filename") or "documento_wuolah.pdf"
    disposition = "inline" if inline else "attachment"

    return FileResponse(
        path=result_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )


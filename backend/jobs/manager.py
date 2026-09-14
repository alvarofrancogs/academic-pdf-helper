import asyncio
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import shutil
from typing import Any, Dict, Optional
import uuid

from backend.browser.wuolah import WuolahBrowser
from backend.core.config import settings
from backend.core.security import sanitize_filename
from backend.pdf.processor import PdfProcessor

logger = logging.getLogger("wuolah.jobs")


class JobStatus:
    QUEUED = "queued"
    STARTING_BROWSER = "starting_browser"
    WAITING_LOGIN = "waiting_login"
    OPENING_DOCUMENT = "opening_document"
    FINDING_RESOURCE = "finding_resource"
    DOWNLOADING = "downloading"
    ANALYZING = "analyzing"
    NORMALIZING = "normalizing"
    VALIDATING = "validating"
    READY = "ready"
    ERROR = "error"


class JobManager:
    """In-memory job manager with TTL cleanup and lifecycle execution."""

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def get_job_dir(self, job_id: str) -> Path:
        """Return dedicated temporary directory for a specific job."""
        job_dir = settings.temp_path / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def cleanup_job_dir(self, job_id: str) -> None:
        """Remove temporary directory for a job."""
        job_dir = settings.temp_path / job_id
        if job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)

    async def create_job(self, url: str) -> Dict[str, Any]:
        async with self._lock:
            job_id = uuid.uuid4().hex[:12]
            job_data = {
                "job_id": job_id,
                "url": url,
                "status": JobStatus.QUEUED,
                "progress": 0,
                "message": "En cola para procesamiento",
                "result_path": None,
                "filename": "documento_wuolah.pdf",
                "result_metadata": None,
                "error": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            self._jobs[job_id] = job_data
            return job_data

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return self._jobs.get(job_id)

    async def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result_path: Optional[str] = None,
        filename: Optional[str] = None,
        result_metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            if status is not None:
                job["status"] = status
            if progress is not None:
                job["progress"] = progress
            if message is not None:
                job["message"] = message
            if result_path is not None:
                job["result_path"] = result_path
            if filename is not None:
                job["filename"] = filename
            if result_metadata is not None:
                job["result_metadata"] = result_metadata
            if error is not None:
                job["error"] = error
            job["updated_at"] = datetime.now(timezone.utc)
            return job

    async def cleanup_expired_jobs(self) -> None:
        """Automatically remove jobs older than JOB_TTL_MINUTES."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            ttl = timedelta(minutes=settings.JOB_TTL_MINUTES)
            expired_ids = [
                jid for jid, j in self._jobs.items()
                if (now - j["created_at"]) > ttl
            ]
            for jid in expired_ids:
                logger.info(f"Purging expired job {jid}")
                self.cleanup_job_dir(jid)
                del self._jobs[jid]

    async def run_document_pipeline(
        self,
        job_id: str,
        url: str,
        browser: WuolahBrowser,
        processor: Optional[PdfProcessor] = None,
    ) -> None:
        """Run the end-to-end background document acquisition and PDF pipeline."""
        proc = processor or PdfProcessor()
        job_dir = self.get_job_dir(job_id)

        try:
            # 1. Start browser
            await self.update_job(
                job_id,
                status=JobStatus.STARTING_BROWSER,
                progress=10,
                message="Iniciando navegador Chromium...",
            )
            await browser.start()

            # 2. Check login
            await self.update_job(
                job_id,
                status=JobStatus.WAITING_LOGIN,
                progress=20,
                message="Verificando sesión en Wuolah...",
            )
            # Give short check to see if authenticated
            _ = await browser.is_authenticated()

            # 3. Open document
            await self.update_job(
                job_id,
                status=JobStatus.OPENING_DOCUMENT,
                progress=35,
                message="Abriendo documento en Wuolah...",
            )
            await browser.open_document(url)
            await browser.wait_for_document()

            # 4. Find network resource
            await self.update_job(
                job_id,
                status=JobStatus.FINDING_RESOURCE,
                progress=50,
                message="Identificando recurso del documento...",
            )
            resource = await browser.find_document_resource()

            # 5. Downloading bytes
            await self.update_job(
                job_id,
                status=JobStatus.DOWNLOADING,
                progress=65,
                message=f"Recibiendo archivo ({len(resource.data)} bytes)...",
            )
            raw_path = job_dir / "raw_data.bin"
            with open(raw_path, "wb") as f:
                f.write(resource.data)

            # 6. Analyzing
            await self.update_job(
                job_id,
                status=JobStatus.ANALYZING,
                progress=75,
                message="Analizando contenido recibido...",
            )

            # 7. Normalizing
            await self.update_job(
                job_id,
                status=JobStatus.NORMALIZING,
                progress=85,
                message="Ejecutando normalización / desofuscación...",
            )

            # 8. Validating and saving final PDF
            await self.update_job(
                job_id,
                status=JobStatus.VALIDATING,
                progress=95,
                message="Validando estructura final del PDF...",
            )
            final_filename = sanitize_filename(resource.filename or "documento_wuolah.pdf")
            final_path = job_dir / final_filename

            pipeline_result = proc.process(
                raw_data=resource.data,
                output_path=final_path,
                content_type=resource.content_type,
            )

            # 9. Ready
            await self.update_job(
                job_id,
                status=JobStatus.READY,
                progress=100,
                message="PDF preparado correctamente",
                result_path=str(final_path),
                filename=final_filename,
                result_metadata={
                    "pages": pipeline_result["pages"],
                    "size_bytes": pipeline_result["size_bytes"],
                    "size_formatted": pipeline_result["size_formatted"],
                    "pdf_version": pipeline_result["pdf_version"],
                    "detected_type": pipeline_result["detected_type"],
                },
            )
            logger.info(f"Job {job_id} successfully completed: {final_filename}")

        except Exception as e:
            logger.exception(f"Error processing job {job_id}: {e}")
            # On error, clean up immediately as required by specification
            self.cleanup_job_dir(job_id)
            await self.update_job(
                job_id,
                status=JobStatus.ERROR,
                progress=100,
                message="Error durante el procesamiento",
                error=str(e),
            )


# Global job manager singleton
job_manager = JobManager()

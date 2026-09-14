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

    def _save_job_to_disk(self, job: Dict[str, Any]) -> None:
        """Persist job record to disk so history survives server restarts."""
        try:
            import json
            job_id = job["job_id"]
            job_dir = self.get_job_dir(job_id)
            meta_file = job_dir / "job.json"
            to_save = dict(job)
            if isinstance(to_save.get("created_at"), datetime):
                to_save["created_at"] = to_save["created_at"].isoformat()
            if isinstance(to_save.get("updated_at"), datetime):
                to_save["updated_at"] = to_save["updated_at"].isoformat()
            meta_file.write_text(json.dumps(to_save, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"Error saving job {job.get('job_id')} to disk: {e}")

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
            self._save_job_to_disk(job_data)
            return job_data

    @staticmethod
    def _parse_datetime(val: Any) -> Optional[datetime]:
        """Safely parse a datetime object, ISO formatted string, or timestamp."""
        if isinstance(val, datetime):
            if val.tzinfo is None:
                return val.replace(tzinfo=timezone.utc)
            return val
        if isinstance(val, str):
            try:
                clean_val = val[:-1] + "+00:00" if val.endswith("Z") else val
                dt = datetime.fromisoformat(clean_val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                return None
        if isinstance(val, (int, float)):
            try:
                return datetime.fromtimestamp(val, tz=timezone.utc)
            except Exception:
                return None
        return None

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                return job

            # Check if job exists on disk
            job_dir = settings.temp_path / job_id
            if not job_dir.exists():
                return None

            # Try loading saved job.json
            meta_file = job_dir / "job.json"
            if meta_file.exists():
                try:
                    import json
                    data = json.loads(meta_file.read_text(encoding="utf-8"))
                    data["created_at"] = self._parse_datetime(data.get("created_at")) or datetime.now(timezone.utc)
                    data["updated_at"] = self._parse_datetime(data.get("updated_at")) or datetime.now(timezone.utc)
                    self._jobs[job_id] = data
                    return data
                except Exception as e:
                    logger.debug(f"Error reading job.json for {job_id}: {e}")

            # Fallback: check for any .pdf file in job_dir
            pdf_files = list(job_dir.glob("*.pdf"))
            if pdf_files:
                pdf_file = pdf_files[0]
                stat = pdf_file.stat()
                job_data = {
                    "job_id": job_id,
                    "url": "",
                    "status": JobStatus.READY,
                    "progress": 100,
                    "message": "PDF preparado correctamente",
                    "result_path": str(pdf_file),
                    "filename": pdf_file.name,
                    "result_metadata": {
                        "pages": 1,
                        "size_bytes": stat.st_size,
                        "size_formatted": f"{stat.st_size / 1024:.2f} KB",
                    },
                    "error": None,
                    "created_at": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
                    "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                }
                self._jobs[job_id] = job_data
                return job_data

            return None

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
                job = await self.get_job(job_id)
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
            self._save_job_to_disk(job)
            return job

    async def cleanup_expired_jobs(self) -> None:
        """Automatically remove jobs older than JOB_TTL_MINUTES."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            ttl = timedelta(minutes=settings.JOB_TTL_MINUTES)
            expired_ids = []
            for jid, j in list(self._jobs.items()):
                created_at = self._parse_datetime(j.get("created_at"))
                if created_at is None or (now - created_at) > ttl:
                    expired_ids.append(jid)

            for jid in expired_ids:
                logger.info(f"Purging expired job {jid}")
                self.cleanup_job_dir(jid)
                self._jobs.pop(jid, None)

            # Also clean up expired job directories on disk that may not be in memory
            try:
                if settings.temp_path.exists():
                    for item in settings.temp_path.iterdir():
                        if not item.is_dir() or item.name == "browser_profile":
                            continue
                        meta_file = item / "job.json"
                        dir_created_at = None
                        if meta_file.exists():
                            try:
                                import json
                                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                                dir_created_at = self._parse_datetime(meta.get("created_at"))
                            except Exception:
                                pass
                        if dir_created_at is None:
                            try:
                                stat = item.stat()
                                dir_created_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                            except Exception:
                                pass
                        if dir_created_at and (now - dir_created_at) > ttl:
                            logger.info(f"Purging expired job directory from disk: {item.name}")
                            shutil.rmtree(item, ignore_errors=True)
                            self._jobs.pop(item.name, None)
            except Exception as e:
                logger.debug(f"Error during disk cleanup of expired jobs: {e}")

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
            async def handle_status_update(msg: str) -> None:
                await self.update_job(job_id, message=msg)

            resource = await browser.find_document_resource(on_status_update=handle_status_update)

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
                    "expected_pages": getattr(browser, "_expected_pages", None),
                    "size_bytes": pipeline_result["size_bytes"],
                    "size_formatted": pipeline_result["size_formatted"],
                    "pdf_version": pipeline_result["pdf_version"],
                    "detected_type": pipeline_result["detected_type"],
                },
            )
            logger.info(f"Job {job_id} successfully completed: {final_filename} ({pipeline_result['pages']} págs)")

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

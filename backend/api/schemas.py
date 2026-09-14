from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    project: str


class SessionStatusResponse(BaseModel):
    authenticated: bool
    browser_running: bool
    message: str


class ProcessDocumentRequest(BaseModel):
    url: str = Field(..., description="URL of the document on Wuolah (https://wuolah.com/...)")


class ProcessDocumentResponse(BaseModel):
    job_id: str
    status: str


class JobResultMetadata(BaseModel):
    pages: int
    size_bytes: int
    size_formatted: str
    pdf_version: str
    detected_type: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    filename: Optional[str] = None
    result_metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

import os
import tempfile
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env file from project root
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


class Settings(BaseModel):
    PROJECT_NAME: str = "Wuolah PDF Helper"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # Storage & Limits
    MAX_PDF_SIZE_MB: int = Field(default_factory=lambda: int(os.getenv("MAX_PDF_SIZE_MB", "100")))
    JOB_TTL_MINUTES: int = Field(default_factory=lambda: int(os.getenv("JOB_TTL_MINUTES", "30")))
    TEMP_DIR: str = Field(
        default_factory=lambda: os.getenv("TEMP_DIR") or str(Path(__file__).resolve().parent.parent.parent / "data")
    )
    
    # Browser & Auth
    WUOLAH_TOKEN: str | None = Field(
        default_factory=lambda: os.getenv("WUOLAH_TOKEN")
    )
    BROWSER_HEADLESS: bool = Field(
        default_factory=lambda: os.getenv("BROWSER_HEADLESS", "false").lower() in ("true", "1", "yes")
    )
    BROWSER_TIMEOUT_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("BROWSER_TIMEOUT_SECONDS", "120"))
    )
    DOWNLOAD_TIMEOUT_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("DOWNLOAD_TIMEOUT_SECONDS", "120"))
    )
    
    # Security
    ALLOWED_DOMAINS: List[str] = ["wuolah.com", "www.wuolah.com"]
    CORS_ORIGINS: List[str] = ["*"]

    @property
    def max_pdf_size_bytes(self) -> int:
        return self.MAX_PDF_SIZE_MB * 1024 * 1024

    @property
    def temp_path(self) -> Path:
        p = Path(self.TEMP_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()

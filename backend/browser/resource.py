from dataclasses import dataclass
from typing import Optional


@dataclass
class DocumentResource:
    """Represents a downloaded or captured document resource."""
    url: str
    content_type: Optional[str]
    size_bytes: int
    data: bytes
    filename: Optional[str] = None

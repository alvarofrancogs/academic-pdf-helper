from typing import Protocol, runtime_checkable


@runtime_checkable
class PdfNormalizer(Protocol):
    """Protocol defining the interface for document byte normalization."""

    def normalize(self, data: bytes) -> bytes:
        """
        Transform raw document bytes into normalized bytes.
        
        Args:
            data: Raw document bytes received from network or source.
            
        Returns:
            Normalized bytes ready for PDF validation and processing.
        """
        ...

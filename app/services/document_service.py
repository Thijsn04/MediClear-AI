"""
Document processing service.

Converts raw uploaded bytes (PDF, JPEG, PNG) or plain text into a
normalised ProcessedDocument ready for any AI provider.
"""

from __future__ import annotations

import base64
from typing import Optional

from app.core.exceptions import (
    DocumentProcessingError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.core.logging import get_logger
from app.providers.base import ProcessedDocument

logger = get_logger(__name__)

_ACCEPTED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png"}
_ACCEPTED_PDF_TYPE = "application/pdf"
_ACCEPTED_TYPES = _ACCEPTED_IMAGE_TYPES | {_ACCEPTED_PDF_TYPE}


class DocumentService:
    """Handles validation and content extraction for uploaded documents."""

    def __init__(self, max_upload_size_mb: int = 10) -> None:
        self._max_bytes = max_upload_size_mb * 1024 * 1024

    def process_text(self, text: str) -> ProcessedDocument:
        """Wrap a plain text string as a ProcessedDocument."""
        return ProcessedDocument(type="text", text=text)

    def process_upload(
        self,
        content: bytes,
        content_type: str,
        filename: Optional[str] = None,
    ) -> ProcessedDocument:
        """
        Validate and process uploaded file bytes.

        Parameters
        ----------
        content:
            Raw file bytes.
        content_type:
            MIME type reported by the client.
        filename:
            Original filename (for logging only).

        Returns
        -------
        ProcessedDocument
            Ready for use by any AI provider.
        """
        # Normalise the MIME type (strip parameters, lower-case)
        mime = content_type.split(";")[0].strip().lower()

        if mime not in _ACCEPTED_TYPES:
            raise UnsupportedFileTypeError(mime)

        if len(content) > self._max_bytes:
            raise FileTooLargeError(self._max_bytes // (1024 * 1024))

        logger.info(
            "document.processing",
            mime=mime,
            size_kb=len(content) // 1024,
            filename=filename,
        )

        if mime == _ACCEPTED_PDF_TYPE:
            return self._process_pdf(content, filename)
        else:
            return self._process_image(content, mime, filename)

    # ------------------------------------------------------------------
    # Internal processors
    # ------------------------------------------------------------------

    @staticmethod
    def _process_pdf(content: bytes, filename: Optional[str]) -> ProcessedDocument:
        """Extract text from a PDF using pypdf."""
        try:
            from pypdf import PdfReader  # type: ignore[import-untyped]
            import io

            reader = PdfReader(io.BytesIO(content))
            pages: list[str] = []
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    pages.append(extracted.strip())

            text = "\n\n".join(pages)
            if not text.strip():
                raise DocumentProcessingError(
                    "Could not extract any text from the PDF. "
                    "The file may be a scanned image-only PDF. "
                    "Please upload a photo of the document instead."
                )

            logger.info("document.pdf_extracted", pages=len(pages), filename=filename)
            return ProcessedDocument(type="text", text=text, filename=filename)

        except DocumentProcessingError:
            raise
        except Exception as exc:
            raise DocumentProcessingError(
                f"Failed to read PDF: {exc}. "
                "Ensure the file is a valid, non-password-protected PDF."
            ) from exc

    @staticmethod
    def _process_image(
        content: bytes,
        mime: str,
        filename: Optional[str],
    ) -> ProcessedDocument:
        """Validate and encode an image for multimodal providers."""
        try:
            from PIL import Image  # type: ignore[import-untyped]
            import io

            # Validate that it is a real image
            img = Image.open(io.BytesIO(content))
            img.verify()

        except Exception as exc:
            raise DocumentProcessingError(
                f"Could not open image file: {exc}"
            ) from exc

        # Store as base64 so it is safely serialisable across the service layer.
        b64 = base64.b64encode(content)
        logger.info("document.image_prepared", mime=mime, filename=filename)
        return ProcessedDocument(
            type="image",
            image_bytes=b64,  # base64-encoded bytes
            image_media_type=mime,
            filename=filename,
        )

"""
Document processing.

Converts raw uploads (PDF, JPEG, PNG, WEBP) or plain text into a normalised
:class:`ProcessedDocument`. Improvements over the previous version:

* size is validated against the raw bytes (the ASGI body-size guard is the
  first line of defence; this is the second),
* image-only ("scanned") PDFs fall back to OCR when enabled, instead of
  hard-failing,
* images are normalised into a base64 ``ImagePart`` for the providers.
"""

from __future__ import annotations

import base64
import io

from app.core.exceptions import (
    DocumentProcessingError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.core.logging import get_logger
from app.providers.base import ImagePart, ProcessedDocument

logger = get_logger(__name__)

_ACCEPTED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
_ACCEPTED_PDF_TYPE = "application/pdf"
_ACCEPTED_TYPES = _ACCEPTED_IMAGE_TYPES | {_ACCEPTED_PDF_TYPE}


class DocumentService:
    def __init__(self, max_upload_size_mb: int = 10, enable_ocr: bool = True) -> None:
        self._max_bytes = max_upload_size_mb * 1024 * 1024
        self._enable_ocr = enable_ocr

    def process_text(self, text: str) -> ProcessedDocument:
        return ProcessedDocument(type="text", text=text)

    def process_upload(
        self,
        content: bytes,
        content_type: str,
        filename: str | None = None,
    ) -> ProcessedDocument:
        mime = content_type.split(";")[0].strip().lower()
        if mime == "image/jpg":
            mime = "image/jpeg"

        if mime not in _ACCEPTED_TYPES:
            raise UnsupportedFileTypeError(mime)
        if len(content) > self._max_bytes:
            raise FileTooLargeError(self._max_bytes // (1024 * 1024))

        logger.info("document.processing", mime=mime, size_kb=len(content) // 1024)

        if mime == _ACCEPTED_PDF_TYPE:
            return self._process_pdf(content, filename)
        return self._process_image(content, mime, filename)

    # ------------------------------------------------------------------

    def _process_pdf(self, content: bytes, filename: str | None) -> ProcessedDocument:
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            pages = [
                extracted.strip() for page in reader.pages if (extracted := page.extract_text())
            ]
            text = "\n\n".join(pages)
        except DocumentProcessingError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise DocumentProcessingError(
                f"Failed to read PDF: {exc}. Ensure it is a valid, non-password-protected PDF."
            ) from exc

        if text.strip():
            logger.info("document.pdf_extracted", pages=len(pages), filename=filename)
            return ProcessedDocument(type="text", text=text, filename=filename)

        # No embedded text - likely a scan. Try OCR before giving up.
        if self._enable_ocr:
            ocr_text = self._ocr_pdf(content)
            if ocr_text and ocr_text.strip():
                logger.info("document.pdf_ocr", filename=filename)
                return ProcessedDocument(type="text", text=ocr_text, filename=filename)

        raise DocumentProcessingError(
            "Could not extract text from the PDF (it appears to be a scanned "
            "image and OCR is unavailable). Please upload a photo of the "
            "document instead - it will be read by a vision model."
        )

    def _ocr_pdf(self, content: bytes) -> str | None:
        """Best-effort OCR of a scanned PDF. Returns None if OCR deps are absent."""
        try:
            import pytesseract  # type: ignore[import-untyped]
            from pdf2image import convert_from_bytes  # type: ignore[import-untyped]
        except ImportError:
            logger.info("document.ocr_unavailable")
            return None
        try:
            images = convert_from_bytes(content)
            return "\n\n".join(pytesseract.image_to_string(img) for img in images)
        except Exception as exc:  # noqa: BLE001
            logger.warning("document.ocr_failed", error=str(exc))
            return None

    @staticmethod
    def _process_image(content: bytes, mime: str, filename: str | None) -> ProcessedDocument:
        try:
            from PIL import Image

            Image.open(io.BytesIO(content)).verify()
        except Exception as exc:  # noqa: BLE001
            raise DocumentProcessingError(f"Could not open image file: {exc}") from exc

        b64 = base64.b64encode(content).decode()
        return ProcessedDocument(
            type="image",
            image=ImagePart(b64_data=b64, media_type=mime),
            filename=filename,
        )

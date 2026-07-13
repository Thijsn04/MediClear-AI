"""Tests for the result cache and document processing."""

from __future__ import annotations

import io

import pytest

from app.core.exceptions import FileTooLargeError, UnsupportedFileTypeError
from app.models.analysis import StructuredAnalysis
from app.services.cache import InMemoryCache, ResultCache, make_key
from app.services.document_service import DocumentService


@pytest.mark.asyncio
async def test_cache_roundtrip() -> None:
    cache = ResultCache(InMemoryCache(), ttl_seconds=60, enabled=True)
    key = make_key("abc", "en", "B1", "model")
    assert await cache.get(key) is None
    await cache.set(key, StructuredAnalysis(summary="cached"))
    got = await cache.get(key)
    assert got is not None and got.summary == "cached"


@pytest.mark.asyncio
async def test_cache_disabled_is_noop() -> None:
    cache = ResultCache(InMemoryCache(), ttl_seconds=60, enabled=False)
    key = make_key("x")
    await cache.set(key, StructuredAnalysis(summary="nope"))
    assert await cache.get(key) is None


def test_process_text() -> None:
    doc = DocumentService().process_text("Patient has a fever.")
    assert doc.type == "text"
    assert doc.text == "Patient has a fever."


def test_unsupported_file_type() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        DocumentService().process_upload(b"hello", "text/plain", "note.txt")


def test_file_too_large() -> None:
    svc = DocumentService(max_upload_size_mb=0)
    with pytest.raises(FileTooLargeError):
        svc.process_upload(b"x" * 2048, "application/pdf", "big.pdf")


def test_process_png_image() -> None:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buf, format="PNG")
    doc = DocumentService().process_upload(buf.getvalue(), "image/png", "scan.png")
    assert doc.type == "image"
    assert doc.image is not None
    assert doc.image.media_type == "image/png"

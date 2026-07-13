"""Tests for the demo provider and OCR / local-TTS code paths (mocked)."""

from __future__ import annotations

import sys
import types

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app
from app.providers.demo import DemoProvider


@pytest.mark.asyncio
async def test_demo_provider_returns_structured_analysis() -> None:
    provider = DemoProvider()
    from app.providers.base import ProcessedDocument

    result = await provider.analyze_document(
        ProcessedDocument(type="text", text="anything"),
        language_name="English",
        target_level="B1",
        max_tokens=1024,
        temperature=0.2,
    )
    assert result.analysis.document_type.value == "discharge_summary"
    assert result.analysis.medications
    assert result.provider == "demo"


def test_demo_mode_end_to_end_without_keys() -> None:
    """AI_PROVIDER=demo lets the whole API work with no API key configured."""
    from app.dependencies import get_ai_service
    from app.providers.registry import build_provider
    from app.services.ai_service import AIService
    from app.services.cache import InMemoryCache, ResultCache
    from app.services.session_store import InMemorySessionStore
    from app.services.terminology import TerminologyService

    settings = Settings(
        _env_file=None,
        ai_provider="demo",
        rate_limit_enabled=False,
        cache_enabled=False,
        terminology_enabled=True,
    )
    service = AIService(
        provider=build_provider(settings),
        session_store=InMemorySessionStore(),
        cache=ResultCache(InMemoryCache(), ttl_seconds=60, enabled=False),
        settings=settings,
        terminology=TerminologyService(enabled=True, online=False),
    )
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_ai_service] = lambda: service
    client = TestClient(app, raise_server_exceptions=False)

    health = client.get("/api/v1/health").json()
    assert health["ai_provider"] == "demo"
    assert health["status"] == "healthy"

    resp = client.post("/api/v1/analyze", data={"text": "any medical text here", "language": "en"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis"]["document_type"] == "discharge_summary"
    # pneumonia should be grounded by the bundled glossary
    terms = {t["term"]: t for t in data["analysis"]["key_terms"]}
    assert terms["pneumonia"]["source"] == "glossary"


def test_ocr_fallback_invoked_for_textless_pdf(monkeypatch) -> None:
    """A PDF with no embedded text triggers the OCR path; we mock the OCR deps."""
    from app.services.document_service import DocumentService

    svc = DocumentService(enable_ocr=True)

    # Fake pypdf returning a page with no text.
    fake_pypdf = types.ModuleType("pypdf")

    class _Page:
        def extract_text(self):
            return ""

    class _Reader:
        def __init__(self, *_a, **_k):
            self.pages = [_Page()]

    fake_pypdf.PdfReader = _Reader
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)

    # Fake OCR stack.
    fake_pt = types.ModuleType("pytesseract")
    fake_pt.image_to_string = lambda img: "OCR EXTRACTED TEXT"
    fake_p2i = types.ModuleType("pdf2image")
    fake_p2i.convert_from_bytes = lambda content: ["img"]
    monkeypatch.setitem(sys.modules, "pytesseract", fake_pt)
    monkeypatch.setitem(sys.modules, "pdf2image", fake_p2i)

    doc = svc.process_upload(b"%PDF-1.4 fake", "application/pdf", "scan.pdf")
    assert doc.type == "text"
    assert "OCR EXTRACTED TEXT" in (doc.text or "")


@pytest.mark.asyncio
async def test_local_tts_backend_invokes_engine(monkeypatch) -> None:
    """The offline TTS backend drives pyttsx3; we mock the engine and file I/O."""
    from app.services.tts_service import TTSService

    saved = {}

    class _Engine:
        def save_to_file(self, text, path):
            saved["text"] = text
            with open(path, "wb") as fh:
                fh.write(b"RIFFWAVE")

        def runAndWait(self):
            pass

    fake_mod = types.ModuleType("pyttsx3")
    fake_mod.init = lambda: _Engine()
    monkeypatch.setitem(sys.modules, "pyttsx3", fake_mod)

    svc = TTSService(backend="local")
    assert svc.media_type == "audio/wav"
    audio = await svc.synthesize("hello world", "en")
    assert audio == b"RIFFWAVE"
    assert saved["text"] == "hello world"

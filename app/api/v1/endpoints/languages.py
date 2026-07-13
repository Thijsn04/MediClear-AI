"""Languages endpoint — returns all supported languages with metadata."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.languages import LANGUAGES
from app.models.schemas import LanguageInfo, LanguagesResponse

router = APIRouter()


@router.get(
    "/languages",
    response_model=LanguagesResponse,
    summary="List supported languages",
    description="Returns language codes, native and English names, and text direction.",
    tags=["System"],
)
async def list_languages() -> LanguagesResponse:
    return LanguagesResponse(
        languages=[
            LanguageInfo(
                code=lang.code,
                name=lang.native_name,
                english_name=lang.english_name,
                rtl=lang.rtl,
            )
            for lang in LANGUAGES.values()
        ]
    )

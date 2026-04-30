"""Languages endpoint — returns all supported languages."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import LanguageInfo, LanguagesResponse, SUPPORTED_LANGUAGES

router = APIRouter()


@router.get(
    "/languages",
    response_model=LanguagesResponse,
    summary="List supported languages",
    description="Returns all language codes and display names supported by the API.",
    tags=["System"],
)
async def list_languages() -> LanguagesResponse:
    return LanguagesResponse(
        languages=[
            LanguageInfo(code=code, name=name)
            for code, name in SUPPORTED_LANGUAGES.items()
        ]
    )

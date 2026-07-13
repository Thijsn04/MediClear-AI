"""API v1 router - aggregates all endpoint routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import analyze, audio, chat, health, languages, sessions

router = APIRouter(prefix="/api/v1")

router.include_router(health.router)
router.include_router(languages.router)
router.include_router(analyze.router)
router.include_router(chat.router)
router.include_router(sessions.router)
router.include_router(audio.router)

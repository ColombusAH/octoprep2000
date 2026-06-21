"""GET /health — Railway keep-warm. No auth, no DB call, <50ms.
GET /config — public runtime config consumed by the dashboard (mentor URL, etc.).
"""

from fastapi import APIRouter

from config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/config")
async def public_config() -> dict:
    s = get_settings()
    return {
        "mentor_booking_url": s.mentor_booking_url,
        "demo_mode": bool(s.demo_replay),
        "audio_chunk_seconds": s.audio_chunk_seconds,
        "provider_mode": s.provider_mode,
        "claude_fallback_configured": s.fallback_enabled,
        "elevenlabs_fallback_configured": s.stt_fallback_enabled,
    }

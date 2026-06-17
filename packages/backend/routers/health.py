"""GET /health — Railway keep-warm. No auth, no DB call, <50ms."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}

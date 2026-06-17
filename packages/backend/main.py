"""FastAPI app entrypoint.

Single-process backend per TECH-ARCH §10 architectural decision.
All agents = asyncio tasks. In-process pub/sub. No Redis.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config import get_settings
from core.rate_limit import limiter
from db.session import init_db
from routers import audio_ws, feedback_ws, health, sessions, upload, video_ws

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
)
logger = logging.getLogger("octoprep")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting OctoPrep2000 backend (demo_mode=%s)", settings.demo_mode or "off")
    try:
        await init_db()
    except Exception as exc:  # noqa: BLE001
        logger.warning("init_db skipped: %s (Alembic handles migrations in prod)", exc)
    yield
    logger.info("shutdown")


app = FastAPI(title="OctoPrep2000", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(upload.router)
app.include_router(video_ws.router)
app.include_router(audio_ws.router)
app.include_router(feedback_ws.router)

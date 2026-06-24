from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://octoprep:octoprep@localhost:5432/octoprep"
    port: int = 8000

    # Tikal LiteLLM gateway (Vision, PPTX, Content, Report, Audio agents)
    litellm_api_key: str = ""
    litellm_base_url: str = "https://litellm.tikalk.dev/v1"
    litellm_vision_model: str = "gpt-4o"
    litellm_text_model: str = "gpt-4.1-mini"
    litellm_stt_model: str = "eleven-scribe-v1"

    # Anthropic Claude — personal-API-key fallback when the Tikal LiteLLM gateway fails
    # (e.g. shared token budget exhausted during the demo). Empty key disables fallback.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # ElevenLabs Scribe v1 — direct (non-gateway) STT fallback when the LiteLLM gateway
    # fails. Empty key disables fallback (AudioAgent then behaves exactly as today).
    elevenlabs_api_key: str = ""

    # Provider mode: "auto" (default) tries the Tikal gateway first and falls back to
    # the personal-key providers above on error. "direct" flips the order — personal-key
    # providers go first (falling back to the gateway only if THOSE fail). Switch to
    # "direct" the moment you know the gateway is exhausted, without waiting on failures.
    provider_mode: str = "auto"

    # Google Cloud Vision via the Tikal LiteLLM gateway (deterministic face metrics — supplements GPT-4o Vision)
    # Shared gateway route — no per-dev GCP service account needed. Empty disables face detection.
    # This route is authenticated with its own key (not litellm_api_key).
    litellm_vision_annotate_url: str = "https://litellm.tikalk.dev/vision/annotate"
    litellm_vision_annotate_api_key: str = ""
    face_detection_pan_threshold_deg: float = 25.0  # head turn left/right → eye contact lost
    face_detection_tilt_threshold_deg: float = 20.0  # head up/down → eye contact lost
    face_detection_roll_threshold_deg: float = 25.0  # sideways head tilt

    # Behaviour
    vision_timeout_ms: int = 5000
    rate_limit_sessions_per_min: int = 5
    frame_dedup_hamming_threshold: int = 8
    audio_chunk_seconds: int = 2
    stale_slide_seconds: int = 240

    # Content research (Exa articles + Context7 docs) — post-session technical topics only
    exa_api_key: str = ""
    context7_api_key: str = ""
    content_research_enabled: bool = True
    content_research_timeout_s: int = 20
    content_research_retries: int = 1

    # Uploaded video batch analysis (feature 003)
    video_max_duration_s: int = 900  # 15 minutes
    video_max_bytes: int = 1_073_741_824  # 1 GB
    video_analysis_fps: int = 1  # frame sampling rate (hard-capped to ≤5 at use site)
    video_posture_stride_s: int = 10  # seconds between GPT-4o posture batches (cost bound)

    # Audio noise reduction (spectral gating before STT)
    noise_reduction_enabled: bool = True

    # Demo insurance
    demo_mode: str = ""  # "replay" → use canned fixtures

    # Logging — DEBUG for verbose agent/LLM output, INFO (default) for normal operation
    log_level: str = "INFO"

    # CTA
    mentor_booking_url: str = "https://calendly.com/tikal-experts/30min"

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        """Railway/Heroku inject DATABASE_URL as `postgres://` or `postgresql://`
        (libpq scheme). SQLAlchemy's async engine needs the asyncpg driver
        explicitly, so coerce to `postgresql+asyncpg://`. Already-async URLs and
        non-Postgres URLs pass through untouched. Alembic re-maps this to a sync
        driver in migrations/env.py."""
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://") :]
        return v

    @property
    def demo_replay(self) -> bool:
        return self.demo_mode.lower() == "replay"

    @property
    def fallback_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def stt_fallback_enabled(self) -> bool:
        return bool(self.elevenlabs_api_key)

    @property
    def use_direct_providers(self) -> bool:
        return self.provider_mode.lower() == "direct"

    @property
    def exa_enabled(self) -> bool:
        return bool(self.exa_api_key)

    @property
    def context7_enabled(self) -> bool:
        return bool(self.context7_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache

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

    # ElevenLabs Scribe v1 (STT) — unused if STT goes through the LiteLLM gateway above
    elevenlabs_api_key: str = ""

    # Google Cloud Vision (deterministic face metrics — supplements GPT-4o Vision)
    # Path to service-account JSON. If empty, face detection is skipped silently.
    google_application_credentials: str = ""
    face_detection_pan_threshold_deg: float = 25.0  # head turn left/right → eye contact lost
    face_detection_tilt_threshold_deg: float = 20.0  # head up/down → eye contact lost
    face_detection_roll_threshold_deg: float = 25.0  # sideways head tilt

    # Behaviour
    vision_timeout_ms: int = 5000
    rate_limit_sessions_per_min: int = 5
    frame_dedup_hamming_threshold: int = 8
    audio_chunk_seconds: int = 2

    # Demo insurance
    demo_mode: str = ""  # "replay" → use canned fixtures

    # CTA
    mentor_booking_url: str = "https://calendly.com/tikal-experts/30min"

    @property
    def demo_replay(self) -> bool:
        return self.demo_mode.lower() == "replay"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

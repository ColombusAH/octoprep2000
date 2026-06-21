"""Tikal LiteLLM gateway client (primary) + Anthropic Claude personal-key fallback.

Used by PPTX, Vision, Content, Report agents. Each dev runs with their personal
LITELLM_API_KEY ($20 budget each). Vision uses image_url message parts.

When ANTHROPIC_API_KEY is set, call_with_fallback() retries a failed gateway call
directly against Claude before giving up. PROVIDER_MODE controls which one goes
first: "auto" (default) tries the gateway first; "direct" tries Claude first and
falls back to the gateway. See pick_provider_order().
"""

from __future__ import annotations

import base64
from functools import lru_cache

from agno.models.anthropic import Claude
from agno.models.openai import OpenAILike
from anthropic import AsyncAnthropic
from loguru import logger
from openai import AsyncOpenAI

from config import get_settings


@lru_cache(maxsize=1)
def get_text_model() -> OpenAILike:
    s = get_settings()
    return OpenAILike(
        id=s.litellm_text_model,
        api_key=s.litellm_api_key or "missing",
        base_url=s.litellm_base_url,
    )


@lru_cache(maxsize=1)
def get_text_model_fallback() -> Claude | None:
    s = get_settings()
    if not s.fallback_enabled:
        return None
    return Claude(id=s.anthropic_model, api_key=s.anthropic_api_key)


@lru_cache(maxsize=1)
def get_llm() -> AsyncOpenAI:
    s = get_settings()
    return AsyncOpenAI(api_key=s.litellm_api_key or "missing", base_url=s.litellm_base_url)


@lru_cache(maxsize=1)
def get_anthropic_llm() -> AsyncAnthropic | None:
    s = get_settings()
    if not s.fallback_enabled:
        return None
    return AsyncAnthropic(api_key=s.anthropic_api_key)


def encode_image_b64(jpeg_bytes: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes).decode("ascii")


def encode_image_b64_raw(jpeg_bytes: bytes) -> str:
    """Bare base64 (no data: prefix) for the Claude Messages API image source."""
    return base64.b64encode(jpeg_bytes).decode("ascii")


async def call_with_fallback(primary, fallback):
    """Try primary(); on any Exception, retry once via fallback() if configured.

    primary/fallback are zero-arg async callables. fallback=None re-raises the
    original error (today's behavior, unchanged). Logs the exception type (not
    just the message) so a real gateway bug is distinguishable from an outage.
    """
    try:
        return await primary()
    except Exception as exc:  # noqa: BLE001
        if fallback is None:
            raise
        logger.warning(
            "Primary provider call failed ({}: {}), retrying with fallback",
            type(exc).__name__,
            exc,
        )
        return await fallback()


def pick_provider_order(direct_call, gateway_call):
    """Order (primary, secondary) per Settings.provider_mode.

    direct_call may be None when no personal-key provider is configured for this
    call site — gateway is always primary in that case, regardless of mode.
    Either order still falls back to the other on failure via call_with_fallback.
    """
    s = get_settings()
    if s.use_direct_providers:
        if direct_call is not None:
            return direct_call, gateway_call
        logger.warning("PROVIDER_MODE=direct but no fallback API key configured for this call — using gateway")
    return gateway_call, direct_call

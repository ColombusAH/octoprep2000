"""Tikal LiteLLM gateway client. Single OpenAI-compatible AsyncClient.

Used by PPTX, Vision, Content, Report agents. Each dev runs with their personal
LITELLM_API_KEY ($20 budget each). Vision uses image_url message parts.
"""

from __future__ import annotations

import base64
from functools import lru_cache

from openai import AsyncOpenAI
from agno.models.openai import OpenAILike

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
def get_llm() -> AsyncOpenAI:
    s = get_settings()
    return AsyncOpenAI(api_key=s.litellm_api_key or "missing", base_url=s.litellm_base_url)


def encode_image_b64(jpeg_bytes: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes).decode("ascii")

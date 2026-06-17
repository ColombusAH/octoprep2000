"""Shared slowapi Limiter — used by main.py (registration) + sessions.py (decorator)."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from config import get_settings

limiter = Limiter(key_func=get_remote_address)

SESSIONS_LIMIT = f"{get_settings().rate_limit_sessions_per_min}/minute"

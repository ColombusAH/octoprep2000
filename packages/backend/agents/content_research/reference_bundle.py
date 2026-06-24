"""Ephemeral reference material assembled before content LLM evaluation.

Gathered during pre-session PPTX prep, persisted on the session row as JSONB, and
reconstructed at report time (feature 002-pre-session-research).
"""

from __future__ import annotations

from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, Field, ValidationError

ResearchStatus = Literal["full", "partial", "skipped", "not_applicable"]
SnippetSource = Literal["official_docs", "article", "improvement_guide"]
MAX_TOTAL_CHARS = 14_000
MAX_SNIPPET_CHARS = {"official_docs": 1200, "article": 800, "improvement_guide": 800}


class TopicClassification(BaseModel):
    is_technical: bool
    primary_libraries: list[str] = Field(default_factory=list, max_length=2)
    confidence: float = Field(ge=0, le=1)
    rationale: str = ""


class ReferenceSnippet(BaseModel):
    source: SnippetSource
    title: str
    url: str = ""
    excerpt: str
    provider: str


class ReferenceBundle(BaseModel):
    topic: str
    snippets: list[ReferenceSnippet] = Field(default_factory=list)
    providers_attempted: list[str] = Field(default_factory=list)
    providers_succeeded: list[str] = Field(default_factory=list)
    fetch_errors: list[str] = Field(default_factory=list)

    def add_snippet(self, snippet: ReferenceSnippet) -> None:
        cap = MAX_SNIPPET_CHARS.get(snippet.source, 800)
        trimmed = ReferenceSnippet(
            source=snippet.source,
            title=snippet.title[:200],
            url=snippet.url,
            excerpt=snippet.excerpt[:cap],
            provider=snippet.provider,
        )
        key = _dedupe_key(trimmed)
        if any(_dedupe_key(s) == key for s in self.snippets):
            return
        current = sum(len(s.excerpt) for s in self.snippets)
        if current + len(trimmed.excerpt) > MAX_TOTAL_CHARS:
            return
        self.snippets.append(trimmed)

    def blocks_by_source(self) -> tuple[str, str, str]:
        docs = [s for s in self.snippets if s.source == "official_docs"]
        articles = [s for s in self.snippets if s.source == "article"]
        improvements = [s for s in self.snippets if s.source == "improvement_guide"]
        return (
            _format_block(docs, "No official documentation retrieved."),
            _format_block(articles, "No articles retrieved."),
            _format_block(improvements, "No improvement guidance retrieved."),
        )


def _dedupe_key(snippet: ReferenceSnippet) -> str:
    if snippet.url:
        return f"{snippet.provider}:{snippet.url}"
    prefix = snippet.excerpt[:120].strip().lower()
    return f"{snippet.provider}:{snippet.source}:{snippet.title.strip().lower()}:{prefix}"


def _format_block(snippets: list[ReferenceSnippet], empty_msg: str) -> str:
    if not snippets:
        return empty_msg
    parts: list[str] = []
    for s in snippets:
        header = f"### {s.title}" + (f" ({s.url})" if s.url else "")
        parts.append(f"{header}\n{s.excerpt}")
    return "\n\n".join(parts)


def to_jsonb(bundle: ReferenceBundle | None) -> dict[str, Any] | None:
    """Serialize a ReferenceBundle for JSONB persistence on the session row."""
    if bundle is None:
        return None
    return bundle.model_dump()


def from_jsonb(data: dict[str, Any] | None) -> ReferenceBundle | None:
    """Reconstruct a ReferenceBundle from persisted JSONB.

    Returns None for missing/empty/invalid data so the content agent falls back to
    transcript-only analysis (FR-008) instead of failing.
    """
    if not data:
        return None
    try:
        return ReferenceBundle(**data)
    except (ValidationError, TypeError) as exc:
        logger.warning("Discarding unparseable persisted research_bundle: {}", exc)
        return None


def compute_research_status(
    *,
    is_technical: bool,
    attempted: list[str],
    succeeded: list[str],
) -> ResearchStatus:
    if not is_technical:
        return "not_applicable"
    if not attempted:
        return "skipped"
    if succeeded and len(succeeded) >= len(attempted):
        return "full"
    if succeeded:
        return "partial"
    return "skipped"

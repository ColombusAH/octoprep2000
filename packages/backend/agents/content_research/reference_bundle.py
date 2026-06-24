"""Ephemeral reference material assembled before content LLM evaluation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

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


def _format_block(snippets: list[ReferenceSnippet], empty_msg: str) -> str:
    if not snippets:
        return empty_msg
    parts: list[str] = []
    for s in snippets:
        header = f"### {s.title}" + (f" ({s.url})" if s.url else "")
        parts.append(f"{header}\n{s.excerpt}")
    return "\n\n".join(parts)


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

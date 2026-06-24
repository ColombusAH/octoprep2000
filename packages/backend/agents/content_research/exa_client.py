"""Exa client — articles and improvement-oriented search."""

from __future__ import annotations

from loguru import logger

from agents.content_research.errors import ResearchProviderError
from agents.content_research.reference_bundle import ReferenceSnippet
from config import get_settings


async def search_articles(topic: str, *, num_results: int = 5) -> list[ReferenceSnippet]:
    query = f'"{topic}" official features documentation overview'
    return await _search(query, source="article", num_results=num_results)


async def search_improvements(topic: str, *, num_results: int = 5) -> list[ReferenceSnippet]:
    query = f'"{topic}" best practices common mistakes what to cover technical talk'
    return await _search(query, source="improvement_guide", num_results=num_results)


async def _search(
    query: str,
    *,
    source: str,
    num_results: int,
) -> list[ReferenceSnippet]:
    settings = get_settings()
    if not settings.exa_enabled:
        return []

    try:
        from exa_py import AsyncExa
    except ImportError as exc:
        raise ResearchProviderError("exa-py not installed") from exc

    exa = AsyncExa(api_key=settings.exa_api_key)
    try:
        results = await exa.search(
            query,
            num_results=num_results,
            contents={"highlights": True},
        )
    except Exception as exc:  # noqa: BLE001
        raise ResearchProviderError(f"Exa search failed: {exc}") from exc

    snippets: list[ReferenceSnippet] = []
    for item in getattr(results, "results", []) or []:
        title = getattr(item, "title", None) or "Article"
        url = getattr(item, "url", None) or ""
        excerpt = ""
        if hasattr(item, "highlights") and item.highlights:
            excerpt = " ".join(item.highlights)
        elif hasattr(item, "text") and item.text:
            excerpt = item.text
        if not excerpt.strip():
            continue
        snippet_source = "article" if source == "article" else "improvement_guide"
        snippets.append(
            ReferenceSnippet(
                source=snippet_source,
                title=str(title),
                url=str(url),
                excerpt=excerpt.strip(),
                provider="exa",
            )
        )
    logger.debug("Exa returned {} snippets for query={!r}", len(snippets), query[:80])
    return snippets

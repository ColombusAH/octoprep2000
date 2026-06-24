"""Context7 HTTP client — official library documentation."""

from __future__ import annotations

import httpx
from loguru import logger

from agents.content_research.errors import ResearchProviderError
from agents.content_research.reference_bundle import ReferenceSnippet
from config import get_settings

CONTEXT7_BASE = "https://context7.com/api/v2"


def _headers() -> dict[str, str]:
    key = get_settings().context7_api_key
    if key:
        return {"Authorization": f"Bearer {key}"}
    return {}


async def resolve_library(library_name: str, query: str) -> str | None:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{CONTEXT7_BASE}/libs/search",
            params={"libraryName": library_name, "query": query},
            headers=_headers(),
        )
        if resp.status_code >= 400:
            raise ResearchProviderError(f"Context7 search HTTP {resp.status_code}")
        data = resp.json()
        results = data if isinstance(data, list) else data.get("results") or data.get("libraries") or []
        if not results:
            return None
        first = results[0]
        if isinstance(first, str):
            return first
        return first.get("id") or first.get("libraryId")


async def fetch_docs(library_id: str, query: str) -> list[ReferenceSnippet]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{CONTEXT7_BASE}/context",
            params={"libraryId": library_id, "query": query, "type": "json"},
            headers=_headers(),
        )
        if resp.status_code >= 400:
            raise ResearchProviderError(f"Context7 context HTTP {resp.status_code}")
        return _parse_context_response(resp.json(), library_id)


def _excerpt_from_code_list(code_list: object) -> str:
    if not isinstance(code_list, list):
        return ""
    parts: list[str] = []
    for block in code_list:
        if isinstance(block, dict):
            code = block.get("code")
            if code:
                parts.append(str(code).strip())
        elif isinstance(block, str) and block.strip():
            parts.append(block.strip())
    return "\n".join(parts)


def _snippet_from_context_item(item: object, library_id: str) -> ReferenceSnippet | None:
    if isinstance(item, str):
        text = item.strip()
        if not text:
            return None
        return ReferenceSnippet(
            source="official_docs",
            title=f"Docs: {library_id}",
            excerpt=text,
            provider="context7",
        )

    if not isinstance(item, dict):
        return None

    # Context7 v2 infoSnippets
    if item.get("content"):
        title = item.get("breadcrumb") or item.get("pageTitle") or f"Docs: {library_id}"
        url = item.get("pageId") or item.get("url") or ""
        return ReferenceSnippet(
            source="official_docs",
            title=str(title),
            url=str(url),
            excerpt=str(item["content"]).strip(),
            provider="context7",
        )

    # Context7 v2 codeSnippets
    if item.get("codeDescription") or item.get("codeList"):
        title = item.get("codeTitle") or item.get("pageTitle") or f"Docs: {library_id}"
        url = item.get("codeId") or item.get("pageId") or item.get("url") or ""
        parts = [str(item.get("codeDescription", "")).strip()]
        code_text = _excerpt_from_code_list(item.get("codeList"))
        if code_text:
            parts.append(code_text)
        excerpt = "\n\n".join(part for part in parts if part)
        if not excerpt:
            return None
        return ReferenceSnippet(
            source="official_docs",
            title=str(title),
            url=str(url),
            excerpt=excerpt,
            provider="context7",
        )

    # Legacy / generic shapes
    text = item.get("content") or item.get("snippet") or item.get("text") or ""
    if not str(text).strip():
        return None
    title = item.get("title") or item.get("pageTitle") or f"Docs: {library_id}"
    return ReferenceSnippet(
        source="official_docs",
        title=str(title),
        url=str(item.get("url", "")),
        excerpt=str(text).strip(),
        provider="context7",
    )


def _parse_context_response(data: object, library_id: str) -> list[ReferenceSnippet]:
    snippets: list[ReferenceSnippet] = []
    if isinstance(data, str):
        if data.strip():
            snippets.append(
                ReferenceSnippet(
                    source="official_docs",
                    title=f"Docs: {library_id}",
                    excerpt=data.strip(),
                    provider="context7",
                )
            )
        return snippets

    if not isinstance(data, dict):
        return snippets

    items: list[object] = []
    for key in ("infoSnippets", "codeSnippets", "snippets", "results", "context"):
        chunk = data.get(key)
        if not chunk:
            continue
        if isinstance(chunk, dict):
            items.append(chunk)
        elif isinstance(chunk, list):
            items.extend(chunk)

    for item in items:
        if len(snippets) >= 5:
            break
        snippet = _snippet_from_context_item(item, library_id)
        if snippet:
            snippets.append(snippet)

    if not snippets and data.get("text"):
        snippets.append(
            ReferenceSnippet(
                source="official_docs",
                title=f"Docs: {library_id}",
                excerpt=str(data["text"]).strip(),
                provider="context7",
            )
        )
    logger.debug("Context7 returned {} snippets for {}", len(snippets), library_id)
    return snippets

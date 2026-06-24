"""Tests for content research module and report status surfacing."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.content_research.context7_client import (
    _parse_context_response,
    fetch_docs,
    resolve_library,
)
from agents.content_research.exa_client import search_articles
from agents.content_research.fetcher import fetch_reference_bundle
from agents.content_research.reference_bundle import (
    ReferenceBundle,
    ReferenceSnippet,
    TopicClassification,
    compute_research_status,
)
from agents.report_agent import ReportAgent
from agents.schemas import ContentAnalysisPayload, ContentFinding


def test_bundle_caps_total_excerpt_chars():
    bundle = ReferenceBundle(topic="React")
    for i in range(50):
        bundle.add_snippet(
            ReferenceSnippet(
                source="article",
                title=f"Article {i}",
                excerpt="x" * 500,
                provider="exa",
            )
        )
    total = sum(len(s.excerpt) for s in bundle.snippets)
    assert total <= 14_000
    assert len(bundle.snippets) < 50


def test_compute_research_status_matrix():
    assert compute_research_status(is_technical=False, attempted=[], succeeded=[]) == "not_applicable"
    assert compute_research_status(is_technical=True, attempted=[], succeeded=[]) == "skipped"
    assert compute_research_status(is_technical=True, attempted=["exa"], succeeded=["exa"]) == "full"
    assert compute_research_status(is_technical=True, attempted=["exa", "c7"], succeeded=["exa"]) == "partial"


@pytest.mark.asyncio
async def test_fetch_skips_when_no_providers_configured(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "")
    monkeypatch.setenv("CONTEXT7_API_KEY", "")
    from config import get_settings

    get_settings.cache_clear()

    classification = TopicClassification(
        is_technical=True,
        primary_libraries=["react"],
        confidence=0.9,
        rationale="technical",
    )
    bundle = await fetch_reference_bundle("React 19", classification)
    assert bundle.providers_attempted == []
    assert bundle.fetch_errors


def test_context7_parse_v2_response():
    data = {
        "infoSnippets": [
            {
                "pageId": "https://example.com/react-19.md",
                "breadcrumb": "React v19 availability",
                "content": "React v19 is now available on npm!",
            }
        ],
        "codeSnippets": [
            {
                "codeTitle": "Install React 19",
                "codeDescription": "Command to install React 19 using Yarn.",
                "codeId": "https://example.com/upgrade-guide.md",
                "pageTitle": "React 19 Upgrade Guide",
                "codeList": [{"language": "bash", "code": "yarn add react@^19.0.0"}],
            }
        ],
    }
    snippets = _parse_context_response(data, "/reactjs/react.dev")
    assert len(snippets) == 2
    assert snippets[0].title == "React v19 availability"
    assert "React v19 is now available" in snippets[0].excerpt
    assert snippets[1].title == "Install React 19"
    assert "yarn add react" in snippets[1].excerpt


@pytest.mark.asyncio
async def test_context7_resolve_and_fetch():
    search_resp = MagicMock()
    search_resp.status_code = 200
    search_resp.json.return_value = [{"id": "/facebook/react"}]

    context_resp = MagicMock()
    context_resp.status_code = 200
    context_resp.json.return_value = {
        "snippets": [{"title": "Hooks", "content": "useState manages local state."}]
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[search_resp, context_resp])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("agents.content_research.context7_client.httpx.AsyncClient", return_value=mock_client):
        lib_id = await resolve_library("react", "React 19")
        assert lib_id == "/facebook/react"
        snippets = await fetch_docs(lib_id, "React 19 key features")
        assert len(snippets) == 1
        assert snippets[0].source == "official_docs"


@pytest.mark.asyncio
async def test_exa_search_disabled_without_key(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "")
    from config import get_settings

    get_settings.cache_clear()
    assert await search_articles("Kubernetes") == []


def test_report_content_breakdown_partial_status_insight():
    agent = ReportAgent()
    content = ContentAnalysisPayload(
        session_id=uuid.uuid4(),
        topic="React",
        content_score=70,
        findings=[
            ContentFinding(type="STRENGTH", message="Good overview", context_quote="hooks"),
        ],
        research_status="partial",
    )
    insights, score = agent._content_breakdown(content)
    assert score == 70
    assert any("partially available" in i.message for i in insights)


def test_report_content_breakdown_skipped_status_insight():
    agent = ReportAgent()
    content = ContentAnalysisPayload(
        session_id=uuid.uuid4(),
        topic="React",
        content_score=60,
        findings=[],
        research_status="skipped",
    )
    insights, _ = agent._content_breakdown(content)
    assert any("Reference lookup unavailable" in i.message for i in insights)


@pytest.mark.asyncio
async def test_classify_topic_fallback_on_llm_error(monkeypatch):
    from agents.content_research import classifier

    with patch.object(classifier, "call_with_fallback", AsyncMock(side_effect=RuntimeError("boom"))):
        result = await classifier.classify_topic("My sales career journey")
        assert result.is_technical is False

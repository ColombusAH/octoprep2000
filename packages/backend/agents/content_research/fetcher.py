"""Parallel research fetch with timeouts, retries, and graceful degradation."""

from __future__ import annotations

import asyncio

from loguru import logger

from agents.content_research import context7_client, exa_client
from agents.content_research.errors import ResearchProviderError
from agents.content_research.reference_bundle import ReferenceBundle, TopicClassification
from config import get_settings


async def fetch_reference_bundle(
    topic: str,
    classification: TopicClassification,
    *,
    include_improvements: bool = True,
) -> ReferenceBundle:
    settings = get_settings()
    bundle = ReferenceBundle(topic=topic)

    if not settings.content_research_enabled or not classification.is_technical:
        return bundle

    tasks: list[tuple[str, asyncio.Task]] = []

    if settings.context7_enabled and classification.primary_libraries:
        tasks.append(("context7", asyncio.create_task(_fetch_context7(topic, classification))))
    if settings.exa_enabled:
        tasks.append(("exa", asyncio.create_task(_fetch_exa(topic, include_improvements))))

    if not tasks:
        bundle.fetch_errors.append("No research providers configured (EXA_API_KEY / CONTEXT7_API_KEY)")
        return bundle

    task_to_name = {task: name for name, task in tasks}
    bundle.providers_attempted = [name for name, _ in tasks]

    done, pending = await asyncio.wait(
        [task for _, task in tasks],
        timeout=settings.content_research_timeout_s,
    )

    for task in pending:
        task.cancel()
        name = task_to_name[task]
        bundle.fetch_errors.append(f"{name}: timed out after {settings.content_research_timeout_s}s")

    for task in done:
        name = task_to_name[task]
        try:
            snippets = task.result()
            if snippets:
                bundle.providers_succeeded.append(name)
                for snippet in snippets:
                    bundle.add_snippet(snippet)
            else:
                bundle.fetch_errors.append(f"{name}: no results")
        except ResearchProviderError as exc:
            bundle.fetch_errors.append(f"{name}: {exc}")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Research provider {} failed", name)
            bundle.fetch_errors.append(f"{name}: {exc}")

    return bundle


async def _fetch_context7(topic: str, classification: TopicClassification) -> list:
    snippets = []
    retries = get_settings().content_research_retries
    for lib in classification.primary_libraries[:2]:
        last_err: Exception | None = None
        for attempt in range(retries + 1):
            try:
                library_id = await context7_client.resolve_library(lib, topic)
                if not library_id:
                    continue
                docs = await context7_client.fetch_docs(
                    library_id, f"{topic} key features API overview"
                )
                snippets.extend(docs)
                break
            except ResearchProviderError as exc:
                last_err = exc
                if attempt < retries:
                    await asyncio.sleep(0.3)
        if last_err and not snippets:
            raise last_err
    return snippets


async def _fetch_exa(topic: str, include_improvements: bool) -> list:
    retries = get_settings().content_research_retries

    async def _with_retry(coro_fn):
        last: Exception | None = None
        for attempt in range(retries + 1):
            try:
                return await coro_fn()
            except ResearchProviderError as exc:
                last = exc
                if attempt < retries:
                    await asyncio.sleep(0.3)
        if last:
            raise last
        return []

    article_coro = _with_retry(lambda: exa_client.search_articles(topic))
    if include_improvements:
        articles, improvements = await asyncio.gather(
            article_coro,
            _with_retry(lambda: exa_client.search_improvements(topic)),
        )
        return list(articles) + list(improvements)
    return await article_coro

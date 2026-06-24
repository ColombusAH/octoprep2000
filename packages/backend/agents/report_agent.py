"""ReportAgent — aggregates all DB logs, deduplicates, scores 4 vectors.

Weights (FR-008):
  Normal:        voice 0.30 + body 0.30 + slide 0.20 + content 0.20
  Audio fallback: voice 0.40 + slide 0.30 + content 0.30 (body omitted)

Per §3 Backend Post-Processing Rule: deduplication is mandatory. Recurring events
are grouped by type into a single insight with a timestamps[]/slides[] array.

Owns its own AsyncSession via get_session_maker() (independent of request scope).
"""

from __future__ import annotations

import uuid
from collections import defaultdict

from agents.content_agent import ContentAnalysisAgent
from agents.persistence import AgentPersistence
from agents.pptx_agent import PPTXAgent
from agents.schemas import (
    ContentAnalysisPayload,
    Insight,
    ReportPayload,
)
from db.repository import PostgreSQLRepository
from db.session import get_session_maker


def _format_slide_insight(description: str, suggested_fix: str, finding_type: str) -> str:
    fix = suggested_fix.strip()
    if finding_type == "IMPROVEMENT" and fix:
        return f"{description} Instead: {fix}"
    return description


class ReportAgent(AgentPersistence):
    def __init__(
        self,
        content_agent: ContentAnalysisAgent | None = None,
        orchestrator=None,
    ) -> None:
        self.content_agent = content_agent or ContentAnalysisAgent()
        self.orchestrator = orchestrator

    async def generate(self, session_id: uuid.UUID, fallback_mode: bool = False) -> ReportPayload:
        async with get_session_maker()() as db:
            repo = PostgreSQLRepository(db)
            session = await repo.get_session(session_id)
            transcripts = await repo.read_transcript(session_id)
            video_events = await repo.read_video_events(session_id)
            audio_warnings = await repo.read_audio_warnings(session_id)

        content = await self.content_agent.analyse(session_id)

        if session and session.slides_raw_text and transcripts:
            pptx = PPTXAgent(self.orchestrator)
            await pptx.analyse_delivery(
                session_id,
                topic=session.topic,
                topic_context=session.topic_context,
                slides_raw=session.slides_raw_text,
                transcript=transcripts,
                content=content,
            )

        async with get_session_maker()() as db:
            repo = PostgreSQLRepository(db)
            slide_analyses = await repo.read_slide_analyses(session_id)

        voice_insights, voice_score = self._score_voice(transcripts, audio_warnings)
        body_insights, body_score = self._score_body(video_events) if not fallback_mode else ([], None)
        slide_insights, slide_score = self._score_slides(slide_analyses)
        content_insights, content_score = self._content_breakdown(content)

        if fallback_mode:
            overall = voice_score * 0.40 + slide_score * 0.30 + content_score * 0.30
        else:
            overall = (
                voice_score * 0.30
                + (body_score or 0) * 0.30
                + slide_score * 0.20
                + content_score * 0.20
            )

        payload = ReportPayload(
            session_id=session_id,
            overall_score=round(overall, 2),
            voice_score=round(voice_score, 2),
            body_score=round(body_score, 2) if body_score is not None else None,
            slide_score=round(slide_score, 2),
            content_score=round(content_score, 2),
            insights=voice_insights + body_insights + slide_insights + content_insights,
        )

        # This agent owns the reports write (Principle II); durability before notify.
        await self._with_repo(
            lambda r: r.insert_report(
                {
                    "session_id": payload.session_id,
                    "overall_score": payload.overall_score,
                    "voice_score": payload.voice_score,
                    "body_score": payload.body_score,
                    "slide_score": payload.slide_score,
                    "content_score": payload.content_score,
                    "insights": [i.model_dump() for i in payload.insights],
                    "mentor_unlocked": payload.mentor_unlocked,
                }
            )
        )
        if self.orchestrator is not None:
            await self.orchestrator.notify_complete(session_id, "REPORT")
        return payload

    # ── per-vector scoring + deduplication ───────────────────────────
    def _score_voice(self, entries, warnings) -> tuple[list[Insight], float]:
        if not entries:
            return [Insight(category="voice", type="IMPROVEMENT", message="No speech captured")], 0.0
        filler_ts: dict[str, list[int]] = defaultdict(list)
        for e in entries:
            for f in e.filler_flags or []:
                filler_ts[f.lower()].append(e.start_ms)

        insights: list[Insight] = []
        total_fillers = sum(len(v) for v in filler_ts.values())
        if filler_ts:
            words = ", ".join(f"'{w}' ({len(ts)}x)" for w, ts in filler_ts.items())
            all_ts = sorted(t for ts in filler_ts.values() for t in ts)
            insights.append(
                Insight(
                    category="voice",
                    type="IMPROVEMENT",
                    message=f"Filler words: {words}. Try pausing instead.",
                    timestamps=all_ts,
                )
            )

        fast_ts = sorted(w.timestamp_ms for w in warnings if w.event_type == "PACING_TOO_FAST")
        slow_ts = sorted(w.timestamp_ms for w in warnings if w.event_type == "PACING_TOO_SLOW")
        if fast_ts:
            insights.append(
                Insight(
                    category="voice",
                    type="IMPROVEMENT",
                    message=f"Spoke too fast at {len(fast_ts)} point(s) — slow down and pause.",
                    timestamps=fast_ts,
                )
            )
        if slow_ts:
            insights.append(
                Insight(
                    category="voice",
                    type="IMPROVEMENT",
                    message=f"Spoke too slowly at {len(slow_ts)} point(s) — pick up the pace.",
                    timestamps=slow_ts,
                )
            )

        penalty = min(40, total_fillers * 2) + min(20, (len(fast_ts) + len(slow_ts)) * 5)
        score = max(0.0, 100.0 - penalty)
        if score > 70 and not fast_ts and not slow_ts:
            insights.append(
                Insight(category="voice", type="STRENGTH", message="Steady pacing & low filler density.")
            )
        return insights, score

    def _score_body(self, events) -> tuple[list[Insight], float]:
        if not events:
            return [], 70.0  # neutral default if no events captured
        grouped: dict[str, list[int]] = defaultdict(list)
        strengths: list[Insight] = []
        for e in events:
            if e.event_type == "SMILING_STRONG":
                # Positive signal from GCV face_detection — surface as a Strength
                strengths.append(
                    Insight(
                        category="body",
                        type="STRENGTH",
                        message="Engaging, smiling delivery.",
                        timestamps=[e.timestamp_ms],
                    )
                )
                continue
            grouped[e.event_type].append(e.timestamp_ms)

        insights: list[Insight] = list(strengths)
        for etype, ts in grouped.items():
            insights.append(
                Insight(
                    category="body",
                    type="IMPROVEMENT",
                    message=f"{etype.replace('_', ' ').title()} ({len(ts)}x)",
                    timestamps=sorted(ts),
                )
            )
        # Score by improvements only — smiles are bonus, don't penalise their absence
        improvement_count = sum(len(ts) for ts in grouped.values())
        penalty = min(40, improvement_count * 2)
        score = max(0.0, 100.0 - penalty)
        return insights, score

    def _score_slides(self, analyses) -> tuple[list[Insight], float]:
        if not analyses:
            return [Insight(category="slide", type="IMPROVEMENT", message="No deck uploaded")], 0.0
        grouped: dict[tuple[int, str], list[tuple[int, str, str]]] = defaultdict(list)
        for a in analyses:
            fix = getattr(a, "suggested_fix", "") or ""
            phase = getattr(a, "analysis_phase", "static") or "static"
            desc = a.description
            if phase == "delivery":
                desc = f"While presenting: {desc}"
            grouped[(a.playbook_factor, a.finding_type)].append((a.slide_index, desc, fix))

        insights: list[Insight] = []
        improvements = 0
        strengths = 0
        for (factor, ftype), items in grouped.items():
            slides = sorted({s for s, _, _ in items})
            desc, fix = items[0][1], items[0][2]
            if len(items) == 1:
                msg = _format_slide_insight(desc, fix, ftype)
            else:
                msg = _format_slide_insight(f"Factor #{factor}: {desc}", fix, ftype)
            insights.append(
                Insight(
                    category="slide",
                    type=ftype,
                    message=msg,
                    slides=slides,
                )
            )
            if ftype == "IMPROVEMENT":
                improvements += 1
            else:
                strengths += 1
        score = max(0.0, 100.0 - improvements * 6 + strengths * 2)
        score = min(100.0, score)
        return insights, score

    def _content_breakdown(
        self, content: ContentAnalysisPayload | None
    ) -> tuple[list[Insight], float]:
        if not content:
            return [Insight(category="content", type="IMPROVEMENT", message="Content analysis skipped")], 0.0
        type_map = {"FACTUAL_ERROR": "IMPROVEMENT", "COVERAGE_GAP": "IMPROVEMENT", "STRENGTH": "STRENGTH"}
        insights = [
            Insight(
                category="content",
                type=type_map.get(f.type, "IMPROVEMENT"),
                message=f.message + (f"  (\"{f.context_quote}\")" if f.context_quote else ""),
            )
            for f in content.findings
        ]
        return insights, float(content.content_score)

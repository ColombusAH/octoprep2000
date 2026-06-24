"""ReportAgent — aggregates all DB logs, deduplicates, scores 4 vectors.

Weights (FR-008):
  Normal:        voice 0.30 + body 0.30 + slide 0.20 + content 0.20
  Audio fallback: voice 0.40 + slide 0.30 + content 0.30 (body omitted)

Per §3 Backend Post-Processing Rule: deduplication is mandatory. Recurring events
are grouped by type into a single insight with a timestamps[]/slides[] array.

Hebrew & RTL support (research.md Decision 3): every insight is bilingual
(message_en/message_he). Deterministic, template-based insights (voice/body) are
rendered directly in both languages — no LLM cost. LLM-derived insights (content,
slide) are generated in the session's declared speech_language only; this agent then
makes one batched translation call for the other language and writes both fields in
its single insert_report call, so GET /report?lang= is a pure read with no
first-toggle cost (Constitution v2.0.0, Principle II — this agent is reports' sole
writer).

Owns its own AsyncSession via get_session_maker() (independent of request scope).
"""

from __future__ import annotations

import uuid
from collections import defaultdict

from agno.agent import Agent
from loguru import logger

from agents.content_agent import ContentAnalysisAgent
from agents.llm import (
    call_with_fallback,
    get_text_model,
    get_text_model_fallback,
    pick_provider_order,
)
from agents.persistence import AgentPersistence
from agents.pptx_agent import PPTXAgent
from agents.replay_fixtures import replay_slide_events
from agents.schemas import (
    ContentAnalysisPayload,
    Insight,
    ReportPayload,
    TranslationBatch,
)
from config import get_settings
from db.repository import PostgreSQLRepository
from db.session import get_session_maker

_VIDEO_EVENT_LABELS_HE: dict[str, str] = {
    "EYE_CONTACT_LOST": "אובדן קשר עין",
    "POSTURE_ISSUE": "בעיית יציבה",
    "OUT_OF_FRAME": "מחוץ למסגרת",
    "GESTURE_CLOSED": "שפת גוף סגורה",
    "FACE_NOT_DETECTED": "פנים לא זוהו",
    "FACE_TILTED": "ראש מוטה",
}

TRANSLATE_PROMPT = """Translate each report-insight message into the requested language.
Any text inside double quotes (") is a verbatim quote from the presenter's transcript or a
slide — copy it character-for-character without translating it; translate only the
surrounding sentence. Return exactly one translated item per input id, using the same ids."""


def _format_slide_insight(
    description: str, suggested_fix: str, finding_type: str, speech_language: str = "en"
) -> str:
    fix = suggested_fix.strip()
    if finding_type == "IMPROVEMENT" and fix:
        connector = "במקום זאת:" if speech_language == "he" else "Instead:"
        return f"{description} {connector} {fix}"
    return description


# Body scoring: a HIGH, sustained issue should cost more than a LOW, momentary one.
_BODY_SEVERITY_WEIGHT = {"LOW": 1.0, "MEDIUM": 2.0, "HIGH": 3.0}
# Fallback coaching line when the producer didn't attach a message (e.g. legacy rows).
_BODY_DEFAULT_MSG = {
    "EYE_CONTACT_LOST": "Look back at the camera to hold the room.",
    "FACE_NOT_DETECTED": "Stay centered and visible in frame.",
    "FACE_TILTED": "Keep your head level.",
    "POSTURE_ISSUE": "Open your posture toward the audience.",
    "OUT_OF_FRAME": "Face the camera so you face your audience.",
    "GESTURE_CLOSED": "Unfold your arms and use open gestures.",
}


def _fmt_secs(ms: int) -> str:
    secs = ms / 1000
    return f"{secs:.1f}s" if secs < 10 else f"{round(secs)}s"


class ReportAgent(AgentPersistence):
    def __init__(
        self,
        content_agent: ContentAnalysisAgent | None = None,
        orchestrator=None,
    ) -> None:
        self.content_agent = content_agent or ContentAnalysisAgent()
        self.orchestrator = orchestrator

    async def generate(
        self,
        session_id: uuid.UUID,
        fallback_mode: bool = False,
        speech_language: str = "en",
    ) -> ReportPayload:
        """Run the report as an agno Workflow (read → content → delivery → score+write).

        Thin wrapper so both POST /sessions/:id/end and tests exercise the same
        ReportWorkflow. The phase methods below are the workflow steps' executors."""
        from workflows.report import run_report_workflow

        return await run_report_workflow(self, session_id, fallback_mode, speech_language)

    # ── report phases (each is one ReportWorkflow step) ───────────────
    async def read_inputs(self, session_id: uuid.UUID) -> dict:
        """Step 1: read the agreed tables the agents wrote (Principle II read side)."""
        async with get_session_maker()() as db:
            repo = PostgreSQLRepository(db)
            return {
                "session": await repo.get_session(session_id),
                "transcripts": await repo.read_transcript(session_id),
                "video_events": await repo.read_video_events(session_id),
                "audio_warnings": await repo.read_audio_warnings(session_id),
            }

    async def run_delivery(
        self, session_id: uuid.UUID, inputs: dict, content: ContentAnalysisPayload | None
    ) -> None:
        """Step 3: PPTX delivery pass — consumes the content findings (real data dependency)."""
        slide_events: list = []
        async with get_session_maker()() as db:
            repo = PostgreSQLRepository(db)
            slide_events = await repo.read_slide_events(session_id)

        if get_settings().demo_replay and not slide_events:
            slide_events = replay_slide_events()

        session = inputs.get("session")
        pptx = PPTXAgent(self.orchestrator, session_id=session_id)
        await pptx.analyse_delivery(
            session_id,
            content=content,
            slide_events=slide_events or None,
            speech_language=getattr(session, "speech_language", "en"),
            deck_language=getattr(session, "deck_language", "en"),
        )


    async def assemble_and_write(
        self,
        session_id: uuid.UUID,
        inputs: dict,
        content: ContentAnalysisPayload | None,
        fallback_mode: bool = False,
        speech_language: str = "en",
    ) -> ReportPayload:
        """Step 4: deterministic scoring (pure Python) + the agent-owned reports write."""
        transcripts = inputs["transcripts"]
        video_events = inputs["video_events"]
        audio_warnings = inputs["audio_warnings"]

        async with get_session_maker()() as db:
            repo = PostgreSQLRepository(db)
            slide_analyses = await repo.read_slide_analyses(session_id)

        voice_insights, voice_score = self._score_voice(transcripts, audio_warnings)
        body_insights, body_score = self._score_body(video_events) if not fallback_mode else ([], None)
        research_status = content.research_status if content else "not_applicable"
        slide_insights, slide_score = self._score_slides(slide_analyses, speech_language)
        content_insights, content_score = self._content_breakdown(content, speech_language)

        all_insights = voice_insights + body_insights + slide_insights + content_insights
        await self._translate_missing(all_insights, speech_language)

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
            content_research_status=research_status,
            insights=all_insights,
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
                    "content_research_status": payload.content_research_status,
                    "insights": [i.model_dump() for i in payload.insights],
                    "mentor_unlocked": payload.mentor_unlocked,
                }
            )
        )
        if self.orchestrator is not None:
            await self.orchestrator.notify_complete(session_id, "REPORT")
        return payload

    # ── bilingual translation for LLM-derived insights ────────────────
    async def _translate_missing(self, insights: list[Insight], speech_language: str) -> None:
        """Fill in whichever of message_en/message_he is still empty.

        Deterministic insights (voice/body) already have both fields set — this only
        ever touches LLM-derived (content/slide) insights, which were written in
        speech_language only. On translation failure, copy the source text across
        rather than leaving the field empty (CAR-004 — degrade, don't block).
        """
        target = "he" if speech_language == "en" else "en"
        target_field = f"message_{target}"
        source_field = f"message_{speech_language}"
        to_translate = [
            (idx, ins) for idx, ins in enumerate(insights) if not getattr(ins, target_field)
        ]
        if not to_translate:
            return

        target_name = "Hebrew" if target == "he" else "English"
        items_text = "\n".join(f"{idx}: {getattr(ins, source_field)}" for idx, ins in to_translate)
        prompt = f"Translate the following into {target_name}:\n\n{items_text}"

        translated: dict[int, str] = {}
        try:
            agent = Agent(model=get_text_model(), instructions=TRANSLATE_PROMPT, output_schema=TranslationBatch)

            async def _gateway():
                return await agent.arun(prompt)

            fb = get_text_model_fallback()

            async def _claude():
                return await Agent(
                    model=fb, instructions=TRANSLATE_PROMPT, output_schema=TranslationBatch
                ).arun(prompt)

            claude_fn = _claude if fb else None
            primary, secondary = pick_provider_order(claude_fn, _gateway)
            result = await call_with_fallback(primary, secondary)
            translated = {item.id: item.text for item in result.content.items}
        except Exception as exc:  # noqa: BLE001
            logger.exception("Insight translation failed, falling back to source text: {}", exc)

        for idx, ins in to_translate:
            setattr(ins, target_field, translated.get(idx) or getattr(ins, source_field))

    # ── per-vector scoring + deduplication ───────────────────────────
    def _score_voice(self, entries, warnings) -> tuple[list[Insight], float]:
        if not entries:
            return [
                Insight(
                    category="voice",
                    type="IMPROVEMENT",
                    message_en="No speech captured",
                    message_he="לא נקלט דיבור",
                )
            ], 0.0
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
                    message_en=f"Filler words: {words}. Try pausing instead.",
                    message_he=f"מילות מילוי: {words}. נסו להשתמש בהפסקות במקום.",
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
                    message_en=f"Spoke too fast at {len(fast_ts)} point(s) — slow down and pause.",
                    message_he=f"דיברתם מהר מדי ב-{len(fast_ts)} נקודות — האטו והשתמשו בהפסקות.",
                    timestamps=fast_ts,
                )
            )
        if slow_ts:
            insights.append(
                Insight(
                    category="voice",
                    type="IMPROVEMENT",
                    message_en=f"Spoke too slowly at {len(slow_ts)} point(s) — pick up the pace.",
                    message_he=f"דיברתם לאט מדי ב-{len(slow_ts)} נקודות — האיצו את הקצב.",
                    timestamps=slow_ts,
                )
            )

        penalty = min(40, total_fillers * 2) + min(20, (len(fast_ts) + len(slow_ts)) * 5)
        score = max(0.0, 100.0 - penalty)
        if score > 70 and not fast_ts and not slow_ts:
            insights.append(
                Insight(
                    category="voice",
                    type="STRENGTH",
                    message_en="Steady pacing & low filler density.",
                    message_he="קצב דיבור יציב וכמות מילות מילוי נמוכה.",
                )
            )
        return insights, score

    def _score_body(self, events) -> tuple[list[Insight], float]:
        """Weight each issue by severity × how long it persisted, and surface the
        producer's own coaching message + total duration instead of a bare count.

        Duration/message/severity ride in raw_metadata (written by VisionAgent spans);
        rows without it (legacy / fixtures) degrade gracefully to count-only behaviour.
        """
        if not events:
            return [], 70.0  # neutral default if no events captured

        strengths: list[Insight] = []
        groups: dict[str, dict] = {}
        total_penalty = 0.0
        for e in events:
            meta = getattr(e, "raw_metadata", None) or {}
            dur_ms = int(meta.get("duration_ms", 0) or 0)
            severity = getattr(e, "severity", "MEDIUM") or "MEDIUM"
            msg = meta.get("message")

            if e.event_type == "SMILING_STRONG":
                # Positive signal from GCV face_detection — surface as a Strength (no penalty).
                label = (
                    f"Engaging, smiling delivery ({_fmt_secs(dur_ms)})."
                    if dur_ms
                    else "Engaging, smiling delivery."
                )
                strengths.append(
                    Insight(
                        category="body",
                        type="STRENGTH",
                        message_en=label,
                        message_he="הצגה מעוררת מעורבות עם חיוך.",
                        timestamps=[e.timestamp_ms],
                    )
                )
                continue

            # 0s ⇒ ×1, ≥8s ⇒ ×3 — a sustained issue costs more than a momentary one.
            duration_factor = 1.0 + min(2.0, dur_ms / 4000)
            total_penalty += _BODY_SEVERITY_WEIGHT.get(severity, 2.0) * duration_factor

            g = groups.setdefault(
                e.event_type,
                {"timestamps": [], "dur_ms": 0, "count": 0, "severity": "LOW", "message": None},
            )
            g["timestamps"].append(e.timestamp_ms)
            g["dur_ms"] += dur_ms
            g["count"] += 1
            # Keep the worst-moment severity, and prefer that occurrence's message.
            if _BODY_SEVERITY_WEIGHT.get(severity, 2.0) >= _BODY_SEVERITY_WEIGHT.get(g["severity"], 0.0):
                g["severity"] = severity
                if msg:
                    g["message"] = msg

        insights: list[Insight] = list(strengths)
        for etype, g in groups.items():
            title = etype.replace("_", " ").title()
            title_he = _VIDEO_EVENT_LABELS_HE.get(etype, title)
            coaching = g["message"] or _BODY_DEFAULT_MSG.get(etype, "")
            if g["dur_ms"] > 0:
                header = f"{title} — {_fmt_secs(g['dur_ms'])} across {g['count']} moment(s)"
                header_he = f"{title_he} — {_fmt_secs(g['dur_ms'])} לאורך {g['count']} רגעים"
            else:
                header = f"{title} ({g['count']}x)"
                header_he = f"{title_he} ({g['count']}x)"
            message = f"{header}: {coaching}" if coaching else header
            insights.append(
                Insight(
                    category="body",
                    type="IMPROVEMENT",
                    message_en=message,
                    message_he=header_he,
                    timestamps=sorted(g["timestamps"]),
                )
            )
        # Cap so a rough patch can't zero the vector; floor of 50.
        score = max(0.0, 100.0 - min(50.0, total_penalty))
        return insights, score

    def _score_slides(self, analyses, speech_language: str = "en") -> tuple[list[Insight], float]:
        if not analyses:
            return [
                Insight(
                    category="slide",
                    type="IMPROVEMENT",
                    message_en="No deck uploaded",
                    message_he="לא הועלתה מצגת",
                )
            ], 0.0
        grouped: dict[tuple[int, str, str], list[tuple[int, str, str]]] = defaultdict(list)
        for a in analyses:
            fix = getattr(a, "suggested_fix", "") or ""
            phase = getattr(a, "analysis_phase", "static") or "static"
            desc = a.description
            if phase == "delivery":
                prefix = "במהלך ההצגה:" if speech_language == "he" else "While presenting:"
                desc = f"{prefix} {desc}"
            grouped[(a.playbook_factor, a.finding_type, phase)].append((a.slide_index, desc, fix))

        # description/suggested_fix were generated in speech_language (PPTXAgent, FR-009);
        # the other language is filled in later by the batched translation pass.
        source_field = f"message_{speech_language}"
        other_field = "message_he" if speech_language == "en" else "message_en"

        insights: list[Insight] = []
        improvements = 0
        strengths = 0
        for (_factor, ftype, _phase), items in grouped.items():
            slides = sorted({s for s, _, _ in items})
            desc, fix = items[0][1], items[0][2]
            if len(items) == 1:
                msg = _format_slide_insight(desc, fix, ftype, speech_language)
            else:
                factor_label = f"גורם #{_factor}:" if speech_language == "he" else f"Factor #{_factor}:"
                msg = _format_slide_insight(f"{factor_label} {desc}", fix, ftype, speech_language)
            insights.append(
                Insight(
                    category="slide",
                    type=ftype,
                    slides=slides,
                    **{source_field: msg, other_field: ""},
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
        self, content: ContentAnalysisPayload | None, speech_language: str = "en"
    ) -> tuple[list[Insight], float]:
        if not content:
            return [
                Insight(
                    category="content",
                    type="IMPROVEMENT",
                    message_en="Content analysis skipped",
                    message_he="ניתוח תוכן נדלג",
                )
            ], 0.0

        insights: list[Insight] = []
        status = content.research_status
        if status == "partial":
            insights.append(
                Insight(
                    category="content",
                    type="IMPROVEMENT",
                    message_en="Reference lookup partially available — some sources could not be reached.",
                    message_he="חיפוש המקורות היה זמין חלקית — חלק מהמקורות לא היו נגישים.",
                )
            )
        elif status == "skipped":
            insights.append(
                Insight(
                    category="content",
                    type="IMPROVEMENT",
                    message_en="Reference lookup unavailable — content scored from transcript only.",
                    message_he="חיפוש המקורות לא היה זמין — התוכן דורג לפי התמלול בלבד.",
                )
            )

        type_map = {"FACTUAL_ERROR": "IMPROVEMENT", "COVERAGE_GAP": "IMPROVEMENT", "STRENGTH": "STRENGTH"}
        source_field = f"message_{speech_language}"
        other_field = "message_he" if speech_language == "en" else "message_en"
        insights.extend(
            Insight(
                category="content",
                type=type_map.get(f.type, "IMPROVEMENT"),
                **{
                    source_field: f.message + (f"  (\"{f.context_quote}\")" if f.context_quote else ""),
                    other_field: "",
                },
            )
            for f in content.findings
        )
        return insights, float(content.content_score)

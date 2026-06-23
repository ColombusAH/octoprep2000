# Product Requirements Document

**Product**: OctoPrep2000
**Version**: 1.6
**Date**: 2026-06-23
**Hackathon Date**: 2026-06-24 (1 day away)
**Author**: Tikal Fuse Day Team
**Status**: Approved — frontend stack sync (v1.6)

> **v1.6 changelog (2026-06-23)** — frontend stack sync, no functional scope change:
> - UI component stack added: **shadcn/ui + Radix UI primitives** (Button, Card, Input, Switch, etc.)
>   styled with Tailwind CSS v4, `class-variance-authority`, `clsx`, `tailwind-merge`,
>   `tw-animate-css`, and `lucide-react` icons — this is the implementation layer for the v1.5
>   Y2K dashboard shell. See §8 and `docs/TECH-ARCHITECTURE-C4.md` §6 for the full stack.
> - **"Spec it" (§8, §13 Appendix D) was a placeholder name — corrected to *Specify / spec-kit***
>   (`https://github.com/tikalk/agentic-sdlc-spec-kit`), Tikal's internal spec-driven-development
>   CLI. It is now actually installed (PR #1, `speckit-init`) — see root `README.md` "Spec-Kit
>   Setup" for the one-time install steps every dev needs to run.
> - New dashboard nav surfaces (Leaderboard, Achievements, Settings) and a dedicated `/start`
>   session-setup page shipped as part of the v1.5 redesign — no new functional requirements;
>   they fall under existing §3 Non-Goals (cosmetic flourishes, no persistence).

> **v1.5 changelog (2026-06-22)** — creative direction pivot, no functional scope change:
> - UI brand direction changed from the original "clinical Whoop/Oura performance-tracker"
>   tone to a **Y2K / VHS-retro** aesthetic. `docs/presentation/octoprep2000-pitch.html` (the
>   team's own pitch deck) is the visual reference — see §10.
> - Gamification is now embraced rather than avoided: the existing mentor lock/unlock mechanic
>   is joined by cosmetic dashboard elements (points wallet, membership-tier badge, mocked
>   "recent sessions" archive). These are visual flourishes only — see §3 Non-Goals, unchanged.
> - `packages/web-dashboard/DESIGN.md` and `PRODUCT.md` are being updated in lockstep to carry
>   this direction. If either still describes the old clinical/anti-gamification tone, this PRD
>   is authoritative — flag the staleness rather than following the older doc.

> **v1.4 changelog (2026-06-17)** — architecture critique fixes applied:
> - Vision API swapped: Google Cloud Vision → **GPT-4o Vision via Tikal LiteLLM** (Google Vision could not do posture/body language)
> - Audio chunk size: 5s → **2s** to meet NFR-002 (≤1s filler latency end-to-end)
> - `topic` field validation tightened (min 8 chars, required)
> - DEMO_MODE replay path added as demo-day insurance
> - `/health` endpoint added; rate limit on `POST /sessions` (5/min/IP)
> - WS browser auto-reconnect with exponential backoff
> - VideoEvent inserts batched in Orchestrator

---

## 1. Executive Summary

OctoPrep2000 is an AI-powered presentation coach. You upload your deck, record your practice session live in the browser, and get a structured report telling you exactly what to fix — with timestamps, slide references, and a score out of 100.

The product is built for **Tikal Fuse Day — June 24, 2026**, with ~6 effective coding hours on the day. Work is organised into three phases to guarantee a working demo regardless of how much gets built. **Phase 1 (first 2 hours)** delivers a lean but fully functional product. Phases 2 and 3 add depth and bonus features. No deployment is required — everything runs locally for the demo. The demo path: upload deck → record session → stop → view report → see score → unlock mentor booking if score ≥ 80.

---

## 2. Problem Statement

Presenters — especially engineers preparing conference talks, internal demos, or customer pitches — have no affordable, immediate feedback loop before going on stage. Professional speaking coaches are expensive and asynchronous. Watching a self-recorded video is tedious, unstructured, and provides no quantified improvement path.

OctoPrep2000 closes this gap by acting as an always-available AI co-pilot that watches, listens, and analyses every dimension of a presenter's rehearsal in real time, then produces a structured, timestamp-anchored report that turns vague impressions into actionable, measurable improvements.

---

## 3. Goals & Non-Goals

### Goals

- **Phase 1 (first 2h)**: working demo — audio feedback with timestamps + PPTX slide analysis + simple report UI.
- **Phase 2**: full 4-vector scorecard — video/body language + technical content accuracy + gamified lock/unlock mechanic.
- **Phase 3 (bonus)**: live in-session feedback with user toggle, Railway deployment, Chrome Extension.
- Build WebSocket infrastructure from Phase 1 so live feedback can be switched on in Phase 3 without rearchitecting.
- All feedback is delivered in the post-session report — that is the core product.

### Non-Goals

- **Live deployment (Railway)** — not required for the demo. Runs locally. Railway is a Phase 3 bonus.
- **Live in-session feedback toasts** — Phase 3 bonus only. If built, must have an ON/OFF toggle so the presenter decides whether to be interrupted during their rehearsal.
- **Chrome Extension UI** — infrastructure is built, UI is deferred to Phase 3.
- Persistent user accounts, multi-session history, or long-term progress tracking (post-hackathon roadmap). The dashboard sidebar's points wallet, membership-tier badge, and "recent sessions" archive (§10) are cosmetic demo flourishes with mocked/local data — they do not imply real accounts, persistence, or backend wiring, and do not lift this non-goal.
- Mobile app or native desktop application.
- Live audience analytics or multi-speaker sessions.
- 60 fps video processing (banned — latency and cost risk).
- Real-time slide-change alignment.
- Real-time technical content checking during the session — content accuracy runs post-session on the full transcript only.

---

## 4. Development Phases

> The team works in phases. Each phase builds on the previous one. If the day runs short, Phase 1 alone is enough to demo.

### 🟢 Phase 1 — Lean MVP (first ~2 hours)

**Goal**: A working demo. User uploads deck, records live, stops, gets a report.

| Feature | Owner |
|---|---|
| PPTX upload + slide analysis (Tikal Playbook) | Dev 4 |
| Live audio recording in browser (record → stop) | Dev 2 |
| STT transcription with timestamps | Dev 2 |
| Filler word detection + WPM analysis | Dev 2 |
| Simple report page: audio findings + slide findings | Dev 5 + Dev 6 |
| WebSocket infrastructure set up (for Phase 3 live feedback) | Dev 1 |

**Phase 1 exit criteria**: user can upload a PPTX, record a 2-minute talk, stop, and see a report that says *"At 2:40 you said a lot of hmm/ahh"* and *"Slide 3 has too much text"*.

---

### 🟡 Phase 2 — Full Product (next ~2–3 hours)

**Goal**: Full 4-vector scorecard with all agents running.

| Feature | Owner |
|---|---|
| Vision Agent — body language, eye contact, posture | Dev 1 |
| Content Accuracy Agent — checks transcript against topic | Dev 3 |
| Topic input field on session start | Dev 6 |
| Full 4-panel scorecard: Voice, Body, Slides, Content | Dev 5 + Dev 6 |
| Gamified lock/unlock mechanic (score ≥ 80) | Dev 6 |
| Session isolation (access token) | Dev 5 |

---

### 🔵 Phase 3 — Bonus (only if time permits)

**Goal**: Extra polish and features if the team is ahead of schedule.

| Feature | Owner |
|---|---|
| Live feedback toasts during session **with ON/OFF toggle** | Dev 6 |
| Railway deployment | Team Lead |
| Chrome Extension UI | Dev 6 |
| PDF export of report | Dev 6 |

> ⚠️ **Live feedback toggle design note**: Some presenters do not want to be interrupted mid-rehearsal. If live feedback is built, the user must be able to toggle it OFF before starting the session. When OFF, all feedback is delivered in the final report only.

---

## 5. User Personas

| Persona | Role | Key Need | Frustration |
|---|---|---|---|
| **The Conference Speaker** | Engineer/expert preparing a tech talk | Structured feedback on pacing, clarity, and slide quality before the event | No affordable real-time coaching; watching self-recordings is unguided |
| **The Internal Presenter** | Developer giving a demo or architecture review | Quick pass/fail signal and specific improvements before the meeting | Prep time is limited; feedback from colleagues is ad hoc |
| **The Tikal Expert / Mentor** | Senior consultant available for 1-on-1 coaching | Only spend time with presenters who are ready for high-quality coaching | Wasted sessions with presenters who haven't done basic self-improvement |
| **The Hackathon Judge** | Technical evaluator scoring the demo | Witness advanced AI orchestration, real-time streaming, and clean architecture | Demos that don't work end-to-end or show shallow AI integration |

---

## 6. User Stories

### Epic 1: Session Setup

- **US-001**: As a presenter, I want to upload my PPTX file before a session so that the system can analyse my slides independently of my live performance.
- **US-002**: As a presenter, I want to enter my talk topic (e.g. "React 19 new features") when starting a session so that the system can evaluate whether my content is technically accurate and complete.
- **US-002b**: As a presenter, I want to start a practice session from the web dashboard so that the backend begins capturing my audio and video via my browser.
- **US-003** `[Phase 3]`: As a presenter, I want to toggle live feedback ON or OFF before starting my session so that I can choose whether to be interrupted during my rehearsal or receive all feedback in the final report only.

### Epic 2: Real-Time Feedback `[Phase 3 — Bonus]`

- **US-004** `[Phase 3]`: As a presenter, I want to see a toast/banner warning ("Speaking too fast!", "Look at the camera") during my rehearsal — only if I turned live feedback ON before starting.
- **US-005** `[Phase 3]`: As a presenter, I want video warnings to appear within 2 seconds of a detected issue so that the feedback is actionable while it is still occurring.
- **US-006** `[Phase 3]`: As a presenter, I want audio feedback (pacing, filler words) to be flagged in real time — only if live feedback is toggled ON.

### Epic 3: Post-Session Scorecard

- **US-007**: As a presenter, I want to view an overall score out of 100 immediately after my session ends so that I have a single headline metric.
- **US-008**: As a presenter, I want each sub-category (Voice, Body Language, Slides, Sync) to show specific "Strengths to Keep" and "Improvements to Change" so that my feedback is actionable and balanced.
- **US-009**: As a presenter, I want recurring issues to be grouped into a single insight with a list of all timestamps so that my report is concise, not repetitive.
- **US-010**: As a presenter scoring below 80, I want to see a locked mentor card explaining exactly how many points I need to earn the unlock so that I have a clear motivation to improve.
- **US-011**: As a presenter scoring 80 or above, I want a celebration animation to trigger and a "Book a 1-on-1 with a Tikal Expert" button to appear so that I can immediately reward myself with expert coaching.

### Epic 4: Slide Analysis

- **US-012**: As a presenter, I want my uploaded PPTX to be evaluated against Tikal's 12-factor Presentation Skills Playbook so that I receive standards-aligned feedback on slide design.
- **US-013**: As a presenter, I want slide-specific feedback (e.g., "Text overload on slides 3, 4, 7") so that I know exactly which slides to fix.

### Epic 5: Technical Content Accuracy

- **US-014**: As a presenter, I want the system to evaluate whether what I said during my session is technically correct so that I don't go on stage with factual errors.
- **US-015**: As a presenter, I want to be told which important topics related to my subject I missed covering so that I can fill the gaps before the real talk.
- **US-016**: As a presenter, I want technically strong explanations explicitly called out as strengths so that I know what to keep and build confidence.
- **US-017**: As a presenter, I want the content analysis to appear in my scorecard as a dedicated sub-category with a score so that it contributes to my overall rating.

### Epic 6: Architecture & Ops

- **US-018**: As the Team Lead, I want all agents to communicate via a shared orchestrator state so that no single service blocks another's stream.
- **US-019**: As the Video Infra Dev, I want the frame extraction service to drop redundant frames algorithmically before forwarding to the Vision agent so that LLM token costs remain within budget.
- **US-020**: As the Team Lead, I want the system to gracefully degrade to audio-only mode if the vision pipeline exceeds latency or cost thresholds so that the demo never fully breaks.

---

## 7. Functional Requirements

### FR-001 `[Phase 1]`: PPTX Upload & Analysis

**Description**: User uploads a `.pptx` file via the web dashboard. The Presentation Analysis Agent evaluates it against Tikal's 12-factor Playbook (layout, text density, visual balance, structural clarity).

**Acceptance Criteria**:
- [ ] User can upload a `.pptx` file ≤ 50 MB via a drag-and-drop or file-picker UI.
- [ ] Analysis completes and is stored in the session record within 30 seconds of upload.
- [ ] Output maps each finding to a specific slide number and a specific Playbook factor.
- [ ] At least 5 distinct Playbook factors are evaluated in the MVP.

---

### FR-002 `[Phase 1]`: Live Session Capture

**Description**: On session start, the browser captures the user's microphone (Phase 1) and optionally webcam (Phase 2). Audio chunks stream via WebSocket to the Audio Agent. Video frames stream to the Frame Service when the Vision Agent is enabled in Phase 2.

**Acceptance Criteria**:
- [ ] `[Phase 1]` Browser requests microphone permission on session start. Camera permission is requested only if video is enabled.
- [ ] `[Phase 1]` WebSocket connection to `ws://backend/audio-stream` established within 3 seconds.
- [ ] `[Phase 1]` Session is assigned a unique `session_id` that namespaces all DB writes.
- [ ] `[Phase 1]` WebSocket infrastructure for `ws://backend/video-stream` and `ws://backend/realtime-feedback` is built and ready — even if not used in Phase 1.
- [ ] `[Phase 2]` Frame service drops duplicate frames before forwarding (≤ 5 fps output to Vision Agent; 60 fps input banned).

---

### FR-003 `[Phase 2]`: Real-Time Video Analysis

**Description**: The Video Analysis Agent subscribes to the optimized frame stream and emits warning events for body language and camera presence issues.

**Acceptance Criteria**:
- [ ] Detected issues (loss of eye contact > 10 s, poor posture, out-of-frame) emit a warning event within 2 seconds of detection.
- [ ] Warning events are published to the `ws://backend/realtime-feedback` pub/sub route.
- [ ] Each event payload includes: `type`, `severity`, `message`, `timestamp_ms`.

---

### FR-004 `[Phase 1]`: Audio Analysis & Transcription

**Description**: The Audio & Transcription Agent processes live audio chunks through a low-latency STT model, commits timestamped transcripts to the DB, and streams text to the Orchestrator.

**Acceptance Criteria**:
- [ ] Audio is segmented into **2-second chunks** for STT processing (v1.4 — was 5s, cut to meet NFR-002).
- [ ] Transcript entries are committed to the DB with `session_id`, `start_ms`, `end_ms`, and `text`.
- [ ] Filler word detection (um, uh, like, you know) triggers a warning event within 1 second of chunk close (≤3s from speaker utterance to toast — within NFR-002 budget).
- [ ] Words-per-minute (WPM) is calculated on a rolling 30-second window; WPM > 160 or < 90 triggers a pacing warning.

---

### FR-005 `[Phase 1 infra / Phase 3 UI]`: Live Feedback Infrastructure + Optional Toasts

**Description**: The WebSocket pub/sub route `ws://backend/realtime-feedback` is built in Phase 1 as infrastructure. The live toast UI is Phase 3 only — and if built, the user must be able to toggle it ON or OFF before starting the session.

**Phase 1 — Infrastructure (must be built even if UI is not)**:
- [ ] Backend exposes `ws://backend/realtime-feedback` pub/sub route scoped by `session_id`.
- [ ] Orchestrator can publish events to connected subscribers on this route.
- [ ] Route is ready to be consumed by a dashboard UI or Chrome Extension without backend changes.

**Phase 3 — Live Toast UI (bonus, only if time permits)**:
- [ ] Before starting a session, user sees a toggle: "Show live feedback during session: ON / OFF". Default is OFF.
- [ ] When OFF: no toasts shown during session. All feedback in final report only.
- [ ] When ON: incoming warning events render as toast overlays (e.g. "Speaking too fast!"). Auto-dismiss after 5 seconds.
- [ ] Toast never fully obscures the camera preview.

**Phase 3 — Chrome Extension (bonus)**:
- [ ] A Chrome Extension (MV3) connects to `ws://backend/realtime-feedback` — zero backend changes required.

---

### FR-006 `[Phase 1]`: Orchestrator

**Description**: The Agno-powered central orchestrator manages shared session state, coordinates concurrent streams, and dispatches events to the correct downstream consumers without blocking.

**Acceptance Criteria**:
- [ ] Orchestrator runs as an async Python service using the `agno` framework.
- [ ] Audio, Video, and (optionally) Slide-change streams are handled concurrently via separate async tasks.
- [ ] Orchestrator state holds at minimum: `session_id`, `active_slide_index`, `transcript_buffer`, `recent_video_events`, `session_status`.
- [ ] Orchestrator triggers Report Generator on `session_status = ENDED`.

---

### FR-007 `[Phase 2]`: Technical Content Analysis Agent

**Description**: Post-session agent that evaluates the technical accuracy and coverage completeness of the presenter's transcript against the stated session topic. Runs after the session ends, alongside the Report Generator. Uses LLM built-in knowledge (no external search).

**Acceptance Criteria**:
- [ ] User provides a `topic` string when creating the session (e.g. "React 19 new features", "Introduction to Kubernetes"). Field is required, min 8 chars, max 200 chars, non-blank. Pydantic-validated at `POST /sessions`; 422 on invalid.
- [ ] Agent reads the full assembled transcript from DB and the session topic.
- [ ] Agent optionally enriches context with slide text from `SlideAnalysis` records.
- [ ] Agent produces a `content_score` (0–100) based on: accuracy of claims made + coverage of expected sub-topics for the stated subject.
- [ ] Agent produces at least: factual errors flagged (if any), coverage gaps (important sub-topics not mentioned), and strong correct explanations highlighted as strengths.
- [ ] Each finding includes a `context_quote` — a verbatim phrase from the transcript that triggered it.
- [ ] Analysis completes and emits `ContentAnalysisPayload` to Orchestrator within 60 seconds of session end.
- [ ] A disclaimer is rendered in the UI beneath the content panel: *"Content accuracy powered by AI training data. May not reflect features released after the model's training cutoff."*

---

### FR-008 `[Phase 1 basic / Phase 2 full]`: Post-Session Report Generation

**Description**: The Report Generator Agent aggregates all DB logs for the session and produces the scorecard. In Phase 1 it covers audio + slides. In Phase 2 it covers all 4 vectors.

**Phase 1 Acceptance Criteria**:
- [ ] Report is generated within 60 seconds of session end.
- [ ] Audio findings: grouped filler word instances with timestamp array (e.g. "Said 'um' 12 times — see: 0:42, 1:15, 2:40").
- [ ] Audio findings: pacing events with timestamps.
- [ ] Slide findings: per-slide issues mapped to Playbook factor.
- [ ] Report rendered at `/session/:id/report`.

**Phase 2 Additions**:
- [ ] Four sub-category scores: Voice 30%, Body Language 30%, Slides 20%, Technical Content 20%.
- [ ] Deduplication across all event types — no repeated line items for the same recurring behaviour.
- [ ] Each sub-category has at least one Strength and one Improvement.
- [ ] Overall score 0–100 with mentor lock/unlock at 80.

---

### FR-009 `[Phase 1 simple / Phase 2 full]`: Scorecard UI

**Description**: The web dashboard renders the post-session scorecard with the Hero Score header, lock/unlock mechanic, and four sub-category panels.

**Acceptance Criteria**:
- [ ] Overall score is displayed prominently (font size ≥ 48 px, numerical + ring/gauge visual).
- [ ] Score < 80: lock icon rendered; motivational copy shows exact delta to 80; "Book" button is hidden/disabled.
- [ ] Score ≥ 80: celebration animation (confetti or equivalent) plays on page load; lock icon replaced with unlock icon; "Book Your 1-on-1 Coaching Session with a Tikal Expert" CTA is rendered and links to the scheduler URL.
- [ ] Four sub-category panels rendered: 🗣️ Voice & Delivery, 🎥 Body Language & Camera, 🖼️ Slide Quality, 🧠 Technical Content Accuracy.
- [ ] Each panel renders Strengths (green) and Improvements (amber/red) with inline timestamp/slide/quote citations.
- [ ] The 🧠 Technical Content panel displays the topic the session was evaluated against, and a disclaimer about AI training cutoff.
- [ ] Report is rendered at `/session/:id/report` and is shareable via that unique URL (read-only view).
- [ ] **Stretch**: An "Export as PDF" button is available on the report page; if time permits, it generates a single-page downloadable PDF of the scorecard.

---

### FR-010a `[Phase 1]`: Demo-Day Hardening (v1.4)

**Description**: Demo-day insurance bundle — `/health` endpoint, browser WS auto-reconnect, `POST /sessions` rate limit, `DEMO_MODE=replay` flag.

**Acceptance Criteria**:
- [ ] `GET /health` returns `{"status":"ok"}` in <50ms, no auth, no DB call. Railway keep-warm pings it every 30s.
- [ ] Browser WS clients reconnect on close with exponential backoff (1s, 2s, 4s, 8s cap). Session state survives reconnect (token in localStorage).
- [ ] `POST /sessions` rate-limited via slowapi: 5 requests / minute / IP. Returns 429 on exceed.
- [ ] `DEMO_MODE=replay` env flag swaps live VisionAgent + AudioAgent calls for canned JSON fixtures (`backend/fixtures/{vision,audio}_events.json`). Only enabled if live APIs fail during demo.

---

### FR-010 `[Phase 2]`: Audio-Only Fallback Mode

**Description**: If the Vision pipeline exceeds a configurable latency or error threshold, the system automatically disables video analysis and continues the session using audio and slide analysis only.

**Acceptance Criteria**:
- [ ] A configurable `VISION_TIMEOUT_MS` env variable (default: 5000 ms) controls the threshold.
- [ ] If Vision Agent fails to respond within threshold for 3 consecutive frames, fallback mode is activated.
- [ ] UI displays a non-blocking banner: "Video analysis unavailable — continuing with audio coaching."
- [ ] Report correctly omits the Body Language sub-category score and adjusts weighting: Voice 40%, Slides 30%, Technical Content 30%.

---

## 7. Non-Functional Requirements

| ID | Category | Requirement | Priority |
|---|---|---|---|
| NFR-001 | Latency | Live warning events delivered to web dashboard toast ≤ 2 s from detection | Critical |
| NFR-002 | Latency | Audio filler-word warning ≤ 3 s end-to-end (v1.4 reconciled with 2s STT chunks; was 1s but unachievable with chunk-based STT) | Critical |
| NFR-003 | Throughput | Video frame pipeline processes ≤ 5 fps output to Vision Agent (60 fps input banned) | Critical |
| NFR-004 | Cost Control | LLM token spend per session capped via frame-drop and audio chunking strategy | High |
| NFR-005 | Availability | Backend deployed on Railway; zero manual restarts required during the demo | High |
| NFR-006 | Scalability | Architecture must support adding new agent types without touching the Orchestrator's pub/sub interface | High |
| NFR-007 | Reliability | Audio-only fallback activates automatically if Vision pipeline degrades (see FR-009) | High |
| NFR-008 | Security | Session IDs are cryptographically random UUIDs; no PII stored beyond transcript text | Medium |
| NFR-009 | Performance | Post-session report generated ≤ 60 s after session ends | High |
| NFR-010 | Compatibility | Chrome Extension (stretch goal) works on Chrome 120+ without browser flag changes | Low |
| NFR-011 | Maintainability | Monorepo managed via `pnpm workspaces`; each service in its own package | Medium |
| NFR-012 | Resilience | Browser WS clients auto-reconnect with exponential backoff (1-8s) on close; reconnect rebinds to same session via stored token | High |
| NFR-013 | Resilience | `POST /sessions` rate-limited (5/min/IP) to prevent demo-URL DoS | High |
| NFR-014 | Resilience | `DEMO_MODE=replay` fixture-replay fallback works for Vision and Audio agents | High |

---

## 8. Integrations & Dependencies

| Integration | Purpose | Owner |
|---|---|---|
| **Agno** | AI agent orchestration framework (Python) | Dev 5 |
| **Tikal LiteLLM** | Internal AI gateway for all LLM calls (PPTX Agent, Content Agent, Report Agent). Base URL: `https://litelm.tikalk.dev/v1`. Each dev uses their own personal API key ($20 budget). | Dev 3, Dev 4, Dev 5 |
| **FastAPI** | Async HTTP + WebSocket backend routing | Dev 1, Dev 5 |
| **GPT-4o Vision (via Tikal LiteLLM)** | Real-time frame analysis for body language, posture, eye contact, framing, gestures. Batched 3 frames per call. Routed through LiteLLM gateway. (v1.4 swap — Google Cloud Vision dropped: face landmarks only, no body language) | Dev 1 |
| **ElevenLabs Scribe v1** | STT for audio transcription (post-session report) | Dev 2 |
| **python-pptx** | PPTX file parsing and content extraction | Dev 4 |
| **Tikal Presentation Skills Playbook** | 12-factor evaluation rubric for slide analysis (internal wiki) | Dev 4 |
| **TanStack Start** | Frontend framework for web dashboard | Dev 6 |
| **shadcn/ui + Radix UI** | UI component primitives for the dashboard (Button, Card, Input, Switch, etc.), styled via Tailwind CSS v4 + `class-variance-authority`/`clsx`/`tailwind-merge` | Dev 6 |
| **Tailwind CSS v4** | Utility CSS framework for dashboard styling (`tw-animate-css` for motion utilities, `lucide-react` for icons) | Dev 6 |
| **Specify (spec-kit)** | Tikal internal spec-driven-development CLI (evaluation multiplier). Installed via `uv tool install agentic-sdlc-specify-cli` — see README "Spec-Kit Setup" | All devs |
| **Railway** | Production hosting and deployment pipeline | Team Lead |
| **Calendly (or equivalent)** | Deep-link URL for mentor booking CTA | Dev 6 |
| **Chrome Extensions API (MV3)** | WebSocket client + floating bubble UI — **stretch goal only** | Dev 6 |
| **pnpm workspaces** | Monorepo package management | Team Lead |

---

## 9. Data Model (High Level)

**Session**: The top-level entity. Has a unique `session_id`, `user_id` (anonymous for MVP), `status` (ACTIVE / ENDED / REPORT_READY), `started_at`, `ended_at`, and a foreign key to `Report`.

**TranscriptEntry**: Belongs to a Session. Stores `start_ms`, `end_ms`, `text`, and `filler_word_flags[]`. Written by the Audio Agent in real time.

**VideoEvent**: Belongs to a Session. Stores `timestamp_ms`, `event_type` (EYE_CONTACT_LOST, POSTURE_ISSUE, etc.), `severity`, and `raw_metadata`. Written by the Video Analysis Agent.

**SlideAnalysis**: Belongs to a Session. Stores `slide_index`, `playbook_factor_id`, `finding_type` (STRENGTH / IMPROVEMENT), and `description`. Written by the PPTX Agent.

**Report**: Belongs to a Session (1-to-1). Stores `overall_score`, `voice_score`, `body_score`, `slide_score`, `content_score`, `voice_insights[]`, `body_insights[]`, `slide_insights[]`, `content_insights[]`, `generated_at`, and `mentor_unlocked` (boolean).

**Insight** (embedded in Report): Each insight has `category`, `type` (STRENGTH / IMPROVEMENT), `message`, `timestamps[]`, and `slides[]`.

---

## 10. UX / UI Principles

- **Creative direction (v1.5): Y2K / VHS-retro.** The team's own pitch deck,
  `docs/presentation/octoprep2000-pitch.html`, is the visual reference — near-black "void"
  background, a teal structural accent plus a single warm orange "hero" accent, the
  Tektur / Space Mono / Chakra Petch type system, and retro CRT motifs (scanlines, grid
  overlay, glitch title reveal, blinking REC dot) applied with restraint to UI chrome. This
  supersedes the earlier "clinical Whoop/Oura performance-tracker" direction.
- **Gamification is embraced, not avoided.** The mentor lock/unlock mechanic below is joined
  by cosmetic dashboard elements — a points wallet, a membership-tier badge, a mocked "recent
  sessions" archive — consistent with the Y2K direction. Earlier guidance to avoid gamified
  badge/streak treatments no longer applies; see §3 Non-Goals for what stays out of scope
  (these remain visual flourishes, not real accounts or persistence).
- **Speed over polish**: The demo must feel live. Latency is a UX metric — decorate UI chrome
  (sidebar, nav, transitions) freely, but keep the capture/record path and report load snappy.
- **Live warning toasts (web dashboard)**: Minimal, non-intrusive overlay. Single line of text, subtle slide-in animation. Never fully obscures the camera preview or slide panel. Auto-dismiss after 5 s.
- **Scorecard hero section**: The overall score is the first thing the eye lands on. Use a bold circular gauge. Colour: red < 60, amber 60–79, green ≥ 80.
- **Lock/unlock mechanic**: The locked state must feel motivational, not punishing. Use warm tones and precise copy ("only 6 points away").
- **Strengths / Improvements split**: Visual parity — equal screen weight given to positive and corrective feedback. Green left panel, amber right panel per sub-category.
- **Timestamp citations**: Clickable (or highlighted) inline citations in insight text linking to the moment in the session recording (stretch: if recording is stored).
- **Accessibility**: Colour is never the sole differentiator — icons and labels always accompany colour coding. Unchanged by the v1.5 creative pivot.
- **Branding**: Visual identity should mirror the team's own pitch deck (above) rather than a generic Tikal/SaaS look — the deck *is* the Tikal Fuse Day artifact for this product.

---

## 11. Open Questions & Risks

> ⚠️ **Timeline constraint**: The hackathon is a single day (June 24) with ~6 effective coding hours. Every item marked **Pre-hackathon** below MUST be answered by June 23 at the latest. Arriving on the day with unresolved tech decisions burns irreplaceable build time.

| # | Question / Risk | Owner | Due |
|---|---|---|---|
| 1 | ~~Which Vision LLM / API?~~ | Dev 1 | ✅ **Decided (v1.4): GPT-4o Vision via Tikal LiteLLM** — multimodal model handles posture, eye contact, framing, gestures. Google Cloud Vision dropped: face landmarks only, no body language. | ~~June 20~~ **Done** |
| 2 | ~~Which STT provider?~~ | Dev 2 | ✅ **Decided: ElevenLabs Scribe v1** — 2-second PCM chunks to meet revised NFR-002 (≤3s end-to-end). | ~~June 20~~ **Done** |
| 3 | ~~Which frame delta library?~~ | Dev 1 | ✅ **Decided: `imagehash` (dhash)** — `pip install imagehash Pillow`. Compare consecutive frames using Hamming distance; drop if ≤ 8 (threshold tunable). Fallback: OpenCV `absdiff`. | ~~June 20~~ **Done** |
| 4 | Will Agno's async task model support three concurrent real-time socket streams without event loop blocking? Validate with a spike. | Dev 5 | **Pre-hackathon** (by June 20) |
| 5 | Is the Tikal internal Playbook wiki accessible programmatically, or must it be embedded verbatim in the system prompt? | Dev 4 | **Pre-hackathon** (by June 20) |
| 6 | Railway pipeline: Is the production environment pre-configured and deployable from CI before June 24? | Team Lead | **Pre-hackathon** (by June 23) |
| 7 | Calendly URL: What is the actual Tikal Expert booking link? Must be a real URL for the demo. | Team Lead | **Pre-hackathon** (by June 23) |
| 8 | Monorepo scaffold: Is `pnpm workspaces` structure committed with all service stubs before June 24 so every dev can start immediately? | Team Lead | **Pre-hackathon** (by June 23) |
| 9 | **Risk**: Vision pipeline latency exceeds budget on the day — mitigation: audio-only fallback (FR-009) must be wired and tested in pre-hackathon spikes. | Dev 2 / Team Lead | **Pre-hackathon** (spike by June 22) |
| 10 | **Risk**: Railway cold-start latency disrupts the demo — mitigation: deploy a keep-warm health-check ping before June 24. | Team Lead | **Pre-hackathon** (by June 23) |
| 11 | *(Stretch)* Chrome Extension auth to `ws://backend/realtime-feedback` (session token in query param?) | Dev 6 | **Hackathon PM** — only if Sprint 1 is done early |
| 12 | Real-time slide-change extension (PPTX Agent): Firm non-goal given 6-hour constraint. Revisit post-hackathon. | Dev 4 / Team Lead | Post-hackathon |

---

## 12. Success Metrics

| Metric | Definition | Target |
|---|---|---|
| **Demo completeness** | End-to-end path works: upload deck → practice → see live warnings in dashboard → view scored report at `/session/:id/report` | 100% (non-negotiable for judging) |
| **Live warning latency** | Median time from event detection to dashboard toast render | ≤ 2 s |
| **Audio feedback latency** | Median time from filler word spoken to warning event published | ≤ 1 s |
| **Report generation time** | Time from session end to report available in UI | ≤ 60 s |
| **PPTX factor coverage** | Number of Tikal Playbook factors evaluated | ≥ 5 factors |
| **Hackathon score** | Judge evaluation score | Top 3 finish |
| **Mentor gate accuracy** | Lock/unlock behaviour triggers correctly at the 80-point threshold | 100% |
| **Fallback resilience** | Audio-only mode activates correctly when Vision pipeline is force-disabled | Verified in demo |

---

## 13. Appendix

### A. Team Responsibilities Summary

| Member | Role | Primary Service |
|---|---|---|
| Team Lead | Product, Integration, Architecture | Cross-cutting; Railway deploy |
| Dev 1 | Full Video Pipeline | Algorithmic Frame Service + Vision Agent (frame capture → deduplication → analysis) |
| Dev 2 | Audio Agent | Live audio streaming, STT, filler word detection, WPM |
| Dev 3 | Content Analysis Agent | Post-session LLM evaluation of transcript for factual accuracy and coverage gaps |
| Dev 4 | PPTX Agent | Post-upload slide analysis against Tikal 12-factor Playbook |
| Dev 5 | Orchestrator + Report Agent | Orchestrator (central brain) + Report Generator (tightly coupled) |
| Dev 6 | Frontend Dashboard | TanStack Start dashboard; Chrome Extension (MV3) stretch only if ahead of schedule |
| Dev 7 | Pitch Presentation & Content | Hackathon pitch deck (Fuse skill framework) + LinkedIn content and social posts for the team |

### B. Score Weighting Formula

```
# Normal (4 vectors):
overall_score = (voice_score   × 0.30)
              + (body_score    × 0.30)
              + (slide_score   × 0.20)
              + (content_score × 0.20)

# Audio-only fallback (Vision pipeline degraded):
overall_score = (voice_score   × 0.40)
              + (slide_score   × 0.30)
              + (content_score × 0.30)

# Note: Presentation Sync retired as a full vector.
# Time-per-slide analysis surfaced as a lightweight finding in Voice & Delivery.
```

### C. WebSocket Route Contract

| Route | Direction | Publisher | Subscriber(s) |
|---|---|---|---|
| `ws://backend/video-stream` | Client → Server | Browser (video capture) | Algorithmic Frame Service |
| `ws://backend/audio-stream` | Client → Server | Browser (mic capture) | Audio & Transcription Agent |
| `ws://backend/realtime-feedback` | Server → Client | Orchestrator (pub/sub) | Web Dashboard (core); Chrome Extension (stretch) |

### D. Glossary

| Term | Definition |
|---|---|
| **Agno** | Python AI agent orchestration framework used as the central brain |
| **PPTX Agent** | Agent responsible for static slide analysis against Tikal's Playbook |
| **Frame Delta** | Algorithmic measure of pixel-level change between consecutive video frames; used to drop redundant frames. Implemented via `imagehash.dhash()` — compares perceptual hash Hamming distance between frames. Threshold = 8 (tunable). |
| **Deduplication Layer** | Backend rule requiring the Report Generator to group recurring event types into a single insight with a timestamp array |
| **Mentor Lock / Unlock** | Gamification mechanic gating access to human coaching behind an 80/100 score threshold |
| **Fuse Day** | Tikal's internal hackathon event |
| **12-Factor Playbook** | Tikal's internal Presentation Skills standard used as the evaluation rubric for slide quality |
| **Railway** | Cloud hosting platform used for the production deployment pipeline |
| **TanStack Start** | Full-stack React framework used for the web dashboard |
| **Specify (spec-kit)** | Tikal's internal spec-driven-development CLI, used as a hackathon evaluation multiplier (formerly referred to as "Spec it" in earlier drafts) |
| **shadcn/ui** | Copy-into-repo UI component pattern built on Radix UI primitives + Tailwind CSS; source of the dashboard's Button/Card/Input/Switch components |

### E. Hackathon Day Schedule — June 24, 2026

> Total available time: ~7–8 hours. Effective coding time after kickoff, lunch, and demo prep: **~6 hours**, split across two sprints.

| Time | Block | Focus | Owner(s) |
|---|---|---|---|
| 09:00–09:30 | 🚀 **Kickoff** | Final scope lock, assign tasks, confirm all services boot locally, unblock any last-minute setup issues | Team Lead |
| 09:30–12:30 | 🏗️ **Sprint 1** (3 h) | Each dev builds their primary service; Team Lead drives integration layer | All devs in parallel |
| 12:30–13:30 | 🍕 **Lunch break** | Rest — do not skip this | Everyone |
| 13:30–15:30 | 🔧 **Sprint 2** (2 h) | Integration, end-to-end wiring, WebSocket connections verified, first full demo run | All devs + Team Lead |
| 15:30–16:00 | 🩹 **Bug fix buffer** (30 min) | Fix critical blockers only; no new features after this point | Team Lead triages |
| 16:00–16:30 | 🎬 **Demo prep** | Rehearse the demo flow, seed test data, verify Railway deploy is live and warm | Dev 6 + Dev 7 |
| 16:30–17:00 | 🏆 **Presentation** | Demo to judges | Team Lead presents |

**Sprint 1 priorities (must be working by 12:30):**
- Dev 1: Frame service accepts WS connection, forwards deduplicated frames; Vision Agent returns at least one event from a test frame
- Dev 2: Audio Agent transcribes a 5-second clip and writes TranscriptEntry to DB
- Dev 3: Content Analysis Agent returns findings for a test transcript + topic (can run against a hardcoded fixture)
- Dev 4: PPTX Agent returns slide findings for a test deck
- Dev 5: Orchestrator boots, connects to all agent streams, triggers report on session end
- Dev 6: Dashboard loads, session start + topic input works, toast renders from a mock event
- Dev 7: Pitch deck scaffolded; draft LinkedIn post written; unblocking whoever is behind

**Sprint 2 priorities (must be working by 15:30):**
- Full end-to-end path: upload deck → start session → live toasts in dashboard → end session → report at `/session/:id/report`
- Lock/unlock mechanic works correctly at the 80-point threshold
- Railway deploy is live and accessible via public URL
- Audio-only fallback activates correctly (quick toggle test)

### G. Reference Links

- Tikal Presentation Skills Playbook (12 Factors): `https://wikijs2.infra.tikalk.dev/en/Playbooks/Presentation-Skills`
- Railway deployment dashboard: (to be added by Team Lead — must be live before June 24)
- Calendly / booking link: (to be added by Team Lead — must be a real URL before June 24)
- Shared Google Drive folder: (to be created by Team Lead — pre-flight action item)

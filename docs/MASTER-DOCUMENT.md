# 🐙 OctoPrep2000 — Master Document

> **Document Purpose**: This document serves as the absolute Single Source of Truth (SSOT) and Master Input for generating the Product Requirement Document (PRD), C4 Architecture Design, Tech Stack Documentation, Mermaid Sequence Diagrams, and Project Milestones.

| | |
|---|---|
| **Document date** | 2026-06-17 (v1.4 — post-critique patch) |
| **Hackathon date** | 2026-06-24 |
| **Days until hackathon** | 7 days |
| **Effective coding time on the day** | ~6 hours (two sprints; lunch excluded) |

> **v1.4 changelog (2026-06-17)**:
> - Vision API: Google Cloud Vision → **GPT-4o Vision via Tikal LiteLLM** (Google Vision dropped, no body language)
> - Audio chunks: 5s → 2s (NFR-002 reconciliation)
> - Demo-day hardening added: `/health`, WS reconnect, rate limit, `DEMO_MODE=replay`, batched VideoEvent inserts, PPTX raw text persisted to DB
> - Agno fallback documented (raw asyncio if Agno PoC fails)

---

## 🏆 Hackathon Context & Product Definition

### The Hackathon Context

This project is being developed within a high-intensity hackathon environment — **Tikal Fuse Day, June 24, 2026**. The team has **18 days of pre-hackathon preparation** (June 6–23) followed by a single build day.

On June 24 the effective coding window is approximately **6 hours**: two focused sprints split by a lunch break, ending with an integration check and demo rehearsal before presenting to judges. This is a hard constraint — there is no Day 2.

**Critical rule**: All architecture decisions, technology selections, API keys, Railway pipeline configuration, and repository scaffolding must be **locked and validated before June 24**. The hackathon day is for building and wiring, not for research or environment setup.

The goal is to build a functional, highly impressive, and scalable MVP that showcases advanced AI agent orchestration, real-time data handling, and high architectural integrity to achieve a winning score.

### What is OctoPrep2000?

OctoPrep2000 is an AI-powered presentation and lecture preparation assistant designed to help speakers, presenters, and tech experts perfect their delivery before going live. Powered by a cutting-edge, real-time agentic backend, the application evaluates a presenter's performance across multiple vectors: verbal pacing, vocal clarity, body language, camera presence, and slide design alignment.

OctoPrep2000 displays immediate, split-second visual warnings as **in-dashboard toast overlays** during a live practice session, and compiles a comprehensive, deeply analytical post-session scorecard rendered at `/session/:id/report`. The backend infrastructure is built Chrome Extension–ready from day one (`ws://backend/realtime-feedback`), but the Extension UI itself is a stretch goal — the dashboard UI is the core delivery target for the hackathon.

---

## 🚀 Immediate Pre-Flight Action Items (For Team Lead)

> All items below must be **completed before June 24**. These are blockers for the hackathon day.

1. **Shared Workspace** *(this week)*: Open a dedicated Shared Google Drive folder to store, share, and track all generated documentation, C4 diagrams, and visual outputs.
2. **Project Scaffolding** *(by June 14)*: Commit the `pnpm workspaces` monorepo with all service stubs so every developer can start immediately on June 24 without setup delays.
3. **Railway Pipeline** *(by June 23)*: Pre-configure the production deployment pipeline and verify it deploys successfully from CI. Add a keep-warm health-check ping so there is no cold-start during the demo.
4. **Calendly / Booking URL** *(by June 23)*: Secure the actual Tikal Expert booking link for the mentor unlock CTA — a placeholder is not acceptable for the live demo.
5. **Technology Decisions Locked** *(✅ done in v1.4)*:
   - **Vision API**: GPT-4o Vision via Tikal LiteLLM (batched 3 frames per call)
   - **STT**: ElevenLabs Scribe v1, 2-second PCM 16kHz chunks
   - **Frame delta**: `imagehash` (dhash), Hamming threshold 8
   - **LLM gateway**: Tikal LiteLLM (`https://litelm.tikalk.dev/v1`) for PPTX, Vision, Content, Report agents

---

## 📅 Core Planning Deliverables

| Deliverable | Deadline | Owner |
|---|---|---|
| **PRD & Architecture Design** — finalize microservices scope and component stack from Tech Radar | June 10 | Team Lead |
| **Scaffolding Session** — group session to set up workspace, absolute paths, and monorepo config | June 14 | Team Lead + All Devs |
| **Technology Spike Results** — Vision API, STT provider, frame-delta library each validated with a working PoC | June 20 | Dev 1, Dev 2, Dev 3 |
| **Agno Orchestrator Spike** — confirm async task model handles 3 concurrent WS streams without blocking | June 20 | Dev 5 |
| **Railway Pipeline Live** — production deploy working from CI; keep-warm configured | June 23 | Team Lead |
| **Presentation Standardization Guide** — internal doc for final pitch web-app quality standards (via Fuse skill framework) | June 23 | Dev 7 |
| **Hackathon Day Kickoff** — all services boot locally, all devs unblocked and ready to build | June 24 09:00 | Team Lead |

---

## 👥 Team Composition & Proposed Staffing (8 Members Total)

The team is structured to support a highly distributed, parallelized end-to-end (UI + BE) microservices model.

| Role | Responsibility |
|---|---|
| **Team Lead** (Product, Integration & Architecture) | Overarching product vision, end-to-end integration, architecture, and Railway deployment |
| **Dev 1** — Full Video Pipeline Developer | Frame Service (capture → deduplication) + Vision Agent (body language, eye contact, posture) — owns the entire video stream end-to-end |
| **Dev 2** — Audio Agent Developer (STT/Audio) | Real-time audio streaming, Speech-to-Text, filler word detection, WPM analysis, timestamped transcripts to DB |
| **Dev 3** — Content Analysis Agent Developer | Post-session agent: reads full transcript + session topic, evaluates technical accuracy and coverage gaps via LLM |
| **Dev 4** — PPTX Agent Developer | Post-upload slide analysis against Tikal's 12-factor Presentation Skills Playbook |
| **Dev 5** — Orchestration & Report Developer (Agno BE) | Agno Orchestrator (central brain, session state, all DB writes) + Report Generator Agent (deduplication, scoring) — tightly coupled, one owner |
| **Dev 6** — Frontend Developer (TanStack Start) | Core web dashboard UI. Chrome Extension UI is a **stretch goal only** — tackled in Hackathon PM if Sprint 1 is finished early |
| **Dev 7** — Pitch Presentation & Content | Hackathon pitch deck (Fuse skill framework) + LinkedIn posts and social content for the team during and after the event |

---

## 🏗️ Agentic Architecture & Real-Time Data Flow

The architecture is inherently event-driven and synchronized over persistent WebSockets, driven by a FastAPI backend and coordinated via Agno.

### 1. 🤖 The Orchestrator (Agno Central Brain)
Acts as the central State Manager and Event Dispatcher. It coordinates asynchronous concurrent real-time streams (Audio, Video Deltas, and optional Slide Changes), cross-references them in a shared state context, and pushes live UI events or final analysis data without blocking parallel processing.

### 2. 📹 Algorithmic Frame Service
A core non-agent utility. It establishes a WebSocket connection with the client, ingests the video feed, and algorithmically discards redundant data, forwarding only optimized frame matrices to save token costs.

### 3. 🤖 Video Analysis Agent (Real-Time Socket-Enabled)
Subscribes to the live frame stream to instantly evaluate presentation presence, posture, and facial framing.

### 4. 🤖 Audio & Transcription Agent (Real-Time Socket-Enabled)
Processes live audio chunks, passes them through a low-latency STT model, commits timestamps to the DB under the unique Session/Video ID, and streams text to the Orchestrator.

### 5. 🤖 Presentation Analysis Agent (PPTX Base Feature)
Ingests the baseline PPTX document uploaded by the user. It evaluates slide layouts, text balance, and visual clarity using the Tikal Presentation Skills Playbook / 12 Factors as its primary contextual guide.
- Reference: https://wikijs2.infra.tikalk.dev/en/Playbooks/Presentation-Skills

> **Optional Real-Time Extension**: Given the single-day 6-hour constraint, real-time slide-change alignment is a **firm non-goal** for the hackathon. Deferred to post-hackathon roadmap.

### 5b. 🤖 Technical Content Analysis Agent *(NEW — replaces Presentation Sync as 4th vector)*
Runs post-session. Reads the full assembled transcript and the session `topic` field provided by the presenter. Uses an LLM to evaluate:
- **Factual accuracy** — are the technical claims correct?
- **Coverage completeness** — what important sub-topics for this subject were not mentioned?
- **Strengths** — which explanations are technically precise and worth keeping?

Each finding is anchored to a verbatim `context_quote` from the transcript. A disclaimer is shown in the UI noting AI training cutoff limitations. Owned by Dev 4 alongside the PPTX Agent — both are post-session content analysis tasks.

### 6. 🤖 Report Generator Agent (Final Scorecard Compiler)
Runs post-presentation. It aggregates data from all asynchronous agent logs, applies deduplication algorithms to group recurring behaviors into singular insights with timestamp arrays, and generates the structured multi-category feedback report.

---

## 📊 End-to-End Product Logic & Report Structure

The final scorecard is the core delivery system of the application, incorporating elements of gamification to drive presenter improvement.

### 1. 🏆 The Top Hero Header (General Score & Milestone Tracker)

This dashboard section sits at the absolute top of the generated report and serves as the product's core gatekeeper feature.

- **The General Score**: A massive, highly visible aggregated score calculated out of 100 points (weighted average of all sub-categories).
- **🔒 The Mentor Lock Constraint (Scores below 80)**: If the general score is lower than 80, a prominent lock icon is displayed alongside motivational copy indicating exactly how many points the user is missing to unlock a human mentor session.
  > *"You scored 74/100. You are only 6 points away from unlocking a 1-on-1 session with a Tikal Expert! Review your targeted improvements and try again."*
  The booking interface remains completely inaccessible.
- **🔓 The Mentor Unlock Event (Scores 80 and above)**: If the general score hits or crosses the 80-point threshold, a celebration animation triggers, the lock flips to open, and a prominent action button is rendered: **[Book Your 1-on-1 Coaching Session with a Tikal Expert]**, directly linking to an active scheduler (e.g., Calendly).

---

### 2. 🎛️ Detailed Sub-Category Metrics (The Strengths & Improvements Model)

Beneath the general score header, the report breaks down into four standalone sections. Every section explicitly formats dynamic feedback into **"🌟 Strengths (To Keep)"** and **"⚠️ Improvements (To Change)"**, mapping issues back to localized timestamps or specific slides.

#### 🗣️ Delivery & Voice (Audio Metric)
Evaluates words-per-minute pacing, vocal energy variations, and awkward gaps.
- **Deduplicated Time-Linked Example**: *"Repetitive filler words: You used the word 'like' / 'um' excessively (24 times total). Try to pause and breathe instead. (See minutes: 01:12, 03:45, 07:22)"*

#### 🎥 Body Language & Camera (Video Metric)
Focuses entirely on camera presence, tracking facial framing, gestures, and posture.
- **Deduplicated Time-Linked Example**: *"Loss of eye contact: You frequently broke eye contact with the lens, looking away for more than 10 seconds at a time. (See minutes: 02:10, 04:55, 05:30)"*

#### 🖼️ Slide Quality & Design (PPTX Metric)
Compares the user's uploaded static presentation against Tikal's internal 12-factor playbook criteria.
- **Slide-Linked Example**: *"Text Overload: Multiple slides violate the 'Keep it visual' rule (Factor #4) and contain dense paragraphs instead of concise bullet points. (See Slides: 3, 4, 7)"*

#### 🧠 Technical Content Accuracy (Content Metric)
Evaluates whether what the presenter said is technically correct and whether important sub-topics for the stated subject were covered. Uses LLM knowledge; runs post-session on the full assembled transcript.
- **Factual Error Example**: *"Incorrect claim detected: You stated that React Server Components were introduced in React 18 — they were stabilised in React 19. (Quote: '…as we got in version 18…')"*
- **Coverage Gap Example**: *"Gap: You covered Server Actions and useTransition but never mentioned the React Compiler — a major React 19 feature audiences will ask about."*
- **Strength Example**: *"Your explanation of the new asset loading API is technically precise and well-sequenced. ✅"*

> **Note**: Presentation Sync is retired as a full scored vector. Stale-slide detection (e.g. "you stayed on Slide 2 for 4+ minutes") surfaces as a lightweight finding inside the Voice & Delivery panel.

---

### 3. 🛠️ Backend Post-Processing Rule (The Deduplication Layer)

To ensure the output is concise and readable, the system enforces a strict backend consolidation constraint.

**The Deduplication Layer**: The Report Generator Agent must execute a deduplication layer over the raw asynchronous database logs. The agent is **strictly prohibited** from generating repetitive line items for recurring behaviors. Instead, it must group identical event signatures into a single macro-insight per section, dynamically appending a consolidated array of all associated timestamps or slide numbers.

---

## 💻 Core Tech Stack & Futureproofing

| Layer | Technology |
|---|---|
| **Repository Layout** | Monorepo architecture controlled via `pnpm workspaces` |
| **Backend Engines** | Python 3.11+, FastAPI (async routing/sockets), `agno` (agent orchestration loops) |
| **Hosting & Infra** | Deployed to a pre-configured production pipeline on Railway |
| **Frontend Evaluation Multipliers** | Native implementation of **Spec it** and **TanStack Start** to maximize hackathon architecture grades ✨ |
| **Futureproof WS Constraint** | Backend exposes `ws://backend/realtime-feedback` pub/sub route — Chrome Extension ready out-of-the-box 🌐 |

---

## ❓ Open Questions & Research Vectors

> ⚠️ With only ~6 effective hours on June 24, **all questions below must be resolved before the hackathon day**. Unresolved decisions on June 24 = wasted build time.

| Question | Owner | Must be resolved by | Status |
|---|---|---|---|
| ~~Vision API choice~~ | Dev 1 | June 20 | ✅ **GPT-4o Vision via LiteLLM** (v1.4) |
| ~~STT provider choice~~ | Dev 2 | June 20 | ✅ **ElevenLabs Scribe v1, 2s chunks** (v1.4) |
| ~~Frame dedup library~~ | Dev 1 | June 20 | ✅ **`imagehash` dhash, threshold 8** |
| **Agno concurrency spike** — confirm 3 concurrent WS streams non-blocking | Dev 5 | June 20 | 🟡 **Fallback locked in v1.4**: raw `asyncio.create_task` if Agno PoC fails |
| Is the Tikal Playbook wiki machine-readable? | Dev 4 | June 20 | 🟡 Open |
| Audio-Only Fallback end-to-end validation | Dev 2 / Dev 5 | June 22 | 🟡 Open |
| `DEMO_MODE=replay` fixture creation + validation | Dev 5 | June 22 | 🆕 v1.4 |

---

## 🗓️ Hackathon Day Schedule — June 24, 2026

> Total available time: ~7–8 hours. **~6 hours of effective coding** across two sprints.

| Time | Block | Goal |
|---|---|---|
| 09:00–09:30 | 🚀 Kickoff | Scope lock, task assignments, confirm all services boot — no surprises |
| 09:30–12:30 | 🏗️ Sprint 1 (3 h) | Each dev builds their primary service to a working stub |
| 12:30–13:30 | 🍕 Lunch | Mandatory rest — do not skip |
| 13:30–15:30 | 🔧 Sprint 2 (2 h) | Integration, end-to-end wiring, first full demo run |
| 15:30–16:00 | 🩹 Bug fix buffer (30 min) | Critical fixes only — **no new features after this point** |
| 16:00–16:30 | 🎬 Demo prep | Rehearse demo flow, seed test data, verify Railway is live and warm |
| 16:30–17:00 | 🏆 Presentation | Demo to judges — Team Lead presents |

**Sprint 1 exit criteria (each dev, by 12:30):**
- Dev 1: Frame service accepts WS connection and forwards frames
- Dev 2: Vision Agent returns at least one event from a test frame
- Dev 3: Audio Agent transcribes a 5-second clip and writes to DB
- Dev 4: PPTX Agent returns findings for a test deck
- Dev 5: Orchestrator boots, connects to all streams, triggers report on session end
- Dev 6: Dashboard loads, session start works, toast renders from a mock event
- Dev 7: Pitch deck scaffolded; unblocking whoever is behind

**Sprint 2 exit criteria (full team, by 15:30):**
- Complete end-to-end path: upload deck → start session → see live toasts → end session → view report at `/session/:id/report`
- Lock/unlock mechanic fires correctly at the 80-point threshold
- Railway deploy accessible via public URL
- Audio-only fallback toggled and verified

---

## 🚀 OctoPrep2000 for the win!

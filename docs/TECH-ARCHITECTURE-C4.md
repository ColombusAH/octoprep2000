# OctoPrep2000 — Technical Architecture (C4)

**System**: OctoPrep2000
**Version**: 1.3
**Date**: 2026-06-17
**Architect**: Tikal Fuse Day Team
**Status**: Approved for implementation — post-critique patch applied (v1.3)

> **v1.3 changelog (2026-06-17)** — addresses architecture critique:
> - **Vision API swapped** to GPT-4o Vision via Tikal LiteLLM (Google Cloud Vision dropped — couldn't do posture/body language)
> - Audio chunk size cut from 5s → 2s to meet NFR-002 (≤1s filler latency)
> - VideoEvent inserts batched (every 1s or N=20) to avoid Orchestrator write bottleneck
> - PPTX text persisted to DB on parse (`slides.raw_text`) — survives container restart
> - `/health` route added; Railway keep-warm pings it
> - `DEMO_MODE=replay` env flag — replays canned events if external APIs flake during demo
> - WS auto-reconnect on browser side with exponential backoff
> - `POST /sessions` rate-limited (slowapi, 5 req/min/IP)
> - `topic` field validated (min 8 chars, non-empty, LLM sanity check)
> - Agno fallback path documented (raw `asyncio.create_task` if Agno PoC fails)
> - Section 10 fallback weights typo fixed (Sync → Content)

---

## Architectural Decisions (locked before writing this doc)

| Decision | Choice | Rationale |
|---|---|---|
| Deployment topology | **Single FastAPI process** | All agents run as `asyncio` tasks inside one app. One Railway service, zero inter-service networking. Correct for a 6-hour build. |
| Database | **PostgreSQL on Railway** | Native Railway plugin, one-click setup, relational model maps cleanly to all entities. |
| PPTX file storage | **Ephemeral /tmp** | Analyse on upload, discard after. Zero setup cost. Acceptable for demo lifecycle. |
| Session ownership | **Backend (Orchestrator)** | `POST /sessions` creates the record and returns a UUID. Frontend never forges IDs. |
| Pub/sub mechanism | **In-process asyncio** | Single process → `asyncio.Queue` + a `dict[session_id → set[WebSocket]]` broadcaster. No Redis needed. |
| Agent write access | **Orchestrator owns all DB writes** | Agents emit typed Pydantic event payloads upward to the Orchestrator. The Orchestrator validates and persists. Agents never import the repository — they are pure AI logic. Agents may read from DB for context. |
| Session isolation | **Session Capability Token** | No user accounts required. `POST /sessions` returns `session_id` + `access_token` (two separate UUIDs). All session operations require both. Report has a separate opt-in `share_token` for read-only sharing. See Section 4.5. |
| Deployment | **Local only for hackathon** | No Railway deployment required. Everything runs locally. Railway is a Phase 3 bonus if time permits. |
| Live feedback UI | **Phase 3 bonus** | WebSocket infrastructure (`ws://backend/realtime-feedback`) is built in Phase 1. Live toast UI + user toggle is Phase 3 only. |

---

## 1. C4 Level 1 — System Context

> Who uses OctoPrep2000, and what external systems does it depend on?

```mermaid
graph TB
    Presenter["👤 Presenter\n[Person]\nUploads deck, starts practice\nsession, receives live coaching\nand post-session scorecard"]

    subgraph OctoPrep["🐙 OctoPrep2000  [Software System]"]
        direction TB
        Core["AI-powered presentation coaching\nReal-time warnings + scored report"]
    end

    VisionAPI["🤖 GPT-4o Vision (via Tikal LiteLLM)\n[External System]\nMultimodal LLM — evaluates posture,\neye contact, framing, gestures from frame batches"]

    STT["🎙️ ElevenLabs Scribe v1\n[External System]\nSpeech-to-Text (Scribe API)\nLive audio transcription"]

    Calendly["📅 Mentor Booking\n[External System]\nCalendly deep-link\nUnlocked at score ≥ 80"]

    Railway["🚂 Railway\n[Infrastructure]\nHosting & CI/CD pipeline\nPostgres plugin included"]

    Presenter -- "HTTPS + WSS\n(browser)" --> OctoPrep
    OctoPrep -- "Frame analysis\nHTTPS REST" --> VisionAPI
    OctoPrep -- "Audio streaming\nHTTPS / WSS" --> STT
    OctoPrep -- "Deep-link redirect\n(read-only)" --> Calendly
    OctoPrep -- "Deployed on" --> Railway
```

**Key constraints visible at this level:**
- The Vision API and STT provider are the **two biggest external latency risks** — both TBD and must be validated in spikes before June 24.
- Calendly is a **deep-link only** — OctoPrep never calls their API.
- Everything runs on a **single Railway project** — no multi-cloud, no CDN for MVP.

---

## 2. C4 Level 2 — Container Diagram

> What are the deployable units inside OctoPrep2000?

```mermaid
graph TB
    Presenter["👤 Presenter\n[Browser]"]

    subgraph Railway["Railway  [Infrastructure]"]

        subgraph WebApp["Web Dashboard  [Container]\nTanStack Start · React · TypeScript\nServed as SSR app\nCaptures webcam + microphone"]
        end

        subgraph Backend["FastAPI Backend  [Container]\nPython 3.11+ · FastAPI · Agno\nSingle process — all agents\nrun as async tasks\nExposes REST + WebSocket routes"]
        end

        subgraph DB["PostgreSQL  [Container]\nRailway managed plugin\nPersists sessions, transcripts,\nvideo events, slide analysis,\nreports"]
        end

    end

    VisionAPI["🤖 Vision LLM API\n[External]"]
    STT["🎙️ STT Provider\n[External]"]

    Presenter -- "HTTPS\nServes pages" --> WebApp
    WebApp -- "REST\nPOST /sessions\nPOST /upload" --> Backend
    WebApp -- "WSS bidirectional\n/video-stream\n/audio-stream" --> Backend
    WebApp -- "WSS receive-only\n/realtime-feedback" --> Backend
    Backend -- "SQL reads/writes\nSQLAlchemy async" --> DB
    Backend -- "HTTPS REST\nframe batches" --> VisionAPI
    Backend -- "HTTPS / WSS\naudio chunks" --> STT
```

**Container responsibilities:**

| Container | Language / Framework | Owns | Talks to |
|---|---|---|---|
| Web Dashboard | TypeScript / TanStack Start | Session UI, live toasts, scorecard rendering | Backend (REST + WSS) |
| FastAPI Backend | Python 3.11+ / FastAPI / Agno | All business logic, all agents, all WebSocket hubs | PostgreSQL, Vision API, STT Provider |
| PostgreSQL | SQL | All persistent data | Backend only |

---

## 3. C4 Level 3 — Component Diagram (FastAPI Backend)

> What are the internal components of the backend, and how do they communicate?

```mermaid
graph TB

    subgraph Backend["FastAPI Backend  [Container]"]

        subgraph Routes["HTTP & WebSocket Routes"]
            SessionRouter["SessionRouter\nPOST /sessions\nGET /sessions/:id\nPOST /sessions/:id/end"]
            UploadRouter["UploadRouter\nPOST /sessions/:id/upload\nSaves PPTX to /tmp"]
            VideoWS["VideoStreamWS\nws://backend/video-stream\nReceives raw frames from browser"]
            AudioWS["AudioStreamWS\nws://backend/audio-stream\nReceives audio chunks from browser"]
            FeedbackWS["FeedbackWS\nws://backend/realtime-feedback\nPub/sub broadcast to dashboard"]
        end

        subgraph Core["Core Services"]
            SessionMgr["SessionManager\nCreates UUID session_id\nManages status transitions\nACTIVE → ENDED → REPORT_READY"]
            Broadcaster["FeedbackBroadcaster\ndict[session_id → set[WebSocket]]\nPublishes warning events\nto all connected dashboard clients"]
        end

        subgraph Orchestrator["Orchestrator"]
            Agno["Orchestrator\nCentral state manager\nSpawns & cancels agent tasks\nper session lifecycle\nHolds shared session context"]
        end

        subgraph Agents["Agents & Services  (async tasks)"]
            FrameSvc["FrameService\n[Non-agent utility]\nImage delta algorithm\n60fps → ≤5fps output\nDrops redundant frames"]
            VisionAgent["VisionAgent\n[Agno Agent]\nAnalyses optimised frames\nDetects eye contact, posture,\nframing issues\nWrites VideoEvent to DB"]
            AudioAgent["AudioAgent\n[Agno Agent]\nChunks audio (≤5s)\nCalls STT provider\nDetects filler words & WPM\nWrites TranscriptEntry to DB"]
            PPTXAgent["PPTXAgent\n[Agno Agent]\nParses PPTX via python-pptx\nEvaluates against 12-factor Playbook\nEmits SlideAnalysisPayload[]"]
        ContentAgent["ContentAnalysisAgent\n[Agno Agent]\nPost-session only\nReads full transcript + topic\nEvaluates technical accuracy\n& coverage gaps via LLM\nEmits ContentAnalysisPayload"]
            ReportAgent["ReportAgent\n[Agno Agent]\nAggregates all DB logs\nDeduplicates recurring events\nCalculates weighted scores\nWrites Report to DB"]
        end

        subgraph DataLayer["Data Layer"]
            Repo["PostgreSQLRepository\nSQLAlchemy async\nCRUD for all entities"]
        end

    end

    VisionAPI["GPT-4o Vision (via Tikal LiteLLM)"]
    STT["STT Provider"]
    DB["PostgreSQL"]

    %% Route → Core
    SessionRouter --> SessionMgr
    FeedbackWS --> Broadcaster
    VideoWS --> Agno
    AudioWS --> Agno
    UploadRouter --> PPTXAgent

    %% Core → Orchestrator
    SessionMgr --> Agno

    %% Orchestrator → Agents (dispatch work)
    Agno --> FrameSvc
    Agno --> VisionAgent
    Agno --> AudioAgent
    Agno --> ReportAgent

    %% Agent pipeline
    FrameSvc --> VisionAgent

    %% Agents → Orchestrator (emit typed event payloads — NO direct DB access)
    VisionAgent -- "emit(VideoEventPayload)" --> Agno
    AudioAgent -- "emit(TranscriptPayload\nAudioWarningPayload)" --> Agno
    PPTXAgent -- "emit(SlideAnalysisPayload[])" --> Agno
    ContentAgent -- "emit(ContentAnalysisPayload)" --> Agno
    ReportAgent -- "emit(ReportPayload)" --> Agno

    %% Orchestrator → Broadcaster (forward warnings to UI)
    Agno --> Broadcaster

    %% Orchestrator is the SOLE WRITER to DB (via repo)
    Agno -- "validate + persist\nall agent payloads" --> Repo

    %% Agents → External APIs (reads only from their domain)
    VisionAgent --> VisionAPI
    AudioAgent --> STT

    %% ReportAgent + ContentAgent read from DB (read-only)
    ReportAgent -. "read-only\n(aggregate events)" .-> Repo
    ContentAgent -. "read-only\n(full transcript)" .-> Repo

    %% ContentAgent also calls Vision LLM for content evaluation
    ContentAgent --> VisionAPI

    %% SessionManager writes session lifecycle state
    SessionMgr --> Repo
    Repo --> DB
```

**Component responsibilities:**

| Component | Type | Responsibility |
|---|---|---|
| `SessionRouter` | FastAPI router | Creates sessions, returns `session_id`, triggers session end |
| `UploadRouter` | FastAPI router | Accepts PPTX multipart upload, saves to `/tmp`, fires `PPTXAgent` |
| `VideoStreamWS` | FastAPI WebSocket | Accepts raw video frames from browser, feeds into `asyncio.Queue` |
| `AudioStreamWS` | FastAPI WebSocket | Accepts audio PCM chunks from browser, feeds into `asyncio.Queue` |
| `FeedbackWS` | FastAPI WebSocket | Clients subscribe by `session_id`; `Broadcaster` pushes events here |
| `SessionManager` | Service | Generates UUID, creates DB record, manages status state machine |
| `FeedbackBroadcaster` | Service | `dict[session_id → set[WebSocket]]`; `publish()` sends to all subscribers |
| `Orchestrator` | Coordinator | Spawns async tasks per session, holds shared state, routes events to Broadcaster. **Sole writer to PostgreSQL** — receives typed payloads from all agents, validates via Pydantic, persists via Repository |
| `FrameService` | Utility (non-agent) — **Dev 1** | Delta algorithm; drops frames below threshold; outputs ≤5fps stream |
| `VisionAgent` | Agno agent — **Dev 1** | Calls GPT-4o Vision (via LiteLLM) per frame batch (≥3 frames per call to amortise tokens); emits `VideoEventPayload` to Orchestrator. **No DB access.** |
| `AudioAgent` | Agno agent — **Dev 2** | Calls STT per chunk; detects filler words + WPM; emits `TranscriptPayload` + `AudioWarningPayload` to Orchestrator. **No DB access.** |
| `PPTXAgent` | Agno agent — **Dev 4** | Runs on upload; evaluates slides against Playbook; emits `SlideAnalysisPayload[]` to Orchestrator. **No DB access.** |
| `ContentAnalysisAgent` | Agno agent — **Dev 3** | Triggered post-session. **Reads** full transcript from DB + session topic. Calls LLM to evaluate factual accuracy and coverage gaps. Emits `ContentAnalysisPayload`. Read-only DB access. |
| `ReportAgent` | Agno agent — **Dev 5** | Triggered on session end; **reads** all events from DB for aggregation; deduplicates + scores (4 vectors); emits `ReportPayload` to Orchestrator. Read-only DB access. |
| `PostgreSQLRepository` | Data layer | All SQLAlchemy models and async CRUD operations. Called exclusively by Orchestrator (writes) and ReportAgent (reads). |

---

## 4. C4 Level 4 — Key Sequence Flows

> How does data actually move during the two critical user journeys?

### 4a. PPTX Upload Flow

```mermaid
sequenceDiagram
    actor Presenter
    participant Dashboard
    participant UploadRouter
    participant PPTXAgent
    participant DB as PostgreSQL

    Presenter->>Dashboard: Drag & drop .pptx file
    Dashboard->>UploadRouter: POST /sessions/:id/upload (multipart)
    UploadRouter->>UploadRouter: Save to /tmp/{session_id}.pptx
    UploadRouter->>PPTXAgent: analyse_async(path, session_id)
    Note over PPTXAgent: Runs as background task<br/>does not block the HTTP response
    UploadRouter-->>Dashboard: 202 Accepted
    Dashboard-->>Presenter: "Analysing your deck…"

    PPTXAgent->>PPTXAgent: python-pptx: extract slide content
    PPTXAgent->>PPTXAgent: LLM: evaluate against 12-factor Playbook
    Note over PPTXAgent: Builds SlideAnalysisPayload[] in memory<br/>Does NOT touch the DB directly
    PPTXAgent->>Orchestrator: emit(SlideAnalysisPayload[])
    Note over Orchestrator: Validates each payload via Pydantic<br/>Rejects malformed findings before they reach DB
    loop Per validated slide finding
        Orchestrator->>DB: INSERT SlideAnalysis(slide_index, factor, finding)
    end
    Orchestrator->>DB: UPDATE Session(pptx_ready=true)
    Dashboard->>Dashboard: Polls GET /sessions/:id until pptx_ready
    Dashboard-->>Presenter: "Deck analysed ✓ — ready to start"
```

---

### 4b. Live Session Flow (Happy Path)

```mermaid
sequenceDiagram
    actor Presenter
    participant Dashboard
    participant SessionRouter
    participant VideoWS as VideoStreamWS
    participant AudioWS as AudioStreamWS
    participant FeedbackWS
    participant Orchestrator
    participant FrameSvc as FrameService
    participant VisionAgent
    participant AudioAgent
    participant Broadcaster as FeedbackBroadcaster
    participant VisionAPI as Vision LLM API
    participant STT as STT Provider
    participant DB as PostgreSQL

    Presenter->>Dashboard: Click "Start Session"
    Dashboard->>SessionRouter: POST /sessions
    SessionRouter->>DB: INSERT Session(session_id, access_token, status=ACTIVE)
    SessionRouter-->>Dashboard: { session_id: "uuid-xxxx", access_token: "uuid-yyyy" }
    Dashboard->>Dashboard: localStorage.set("token_uuid-xxxx", "uuid-yyyy")
    Note over Dashboard: access_token stored in localStorage only<br/>Never placed in the URL

    par Open 3 WebSocket connections (all include token)
        Dashboard->>VideoWS: connect ?session_id=uuid-xxxx&token=uuid-yyyy
        Dashboard->>AudioWS: connect ?session_id=uuid-xxxx&token=uuid-yyyy
        Dashboard->>FeedbackWS: connect ?session_id=uuid-xxxx&token=uuid-yyyy
    end

    Note over VideoWS,FeedbackWS: Each WS handler validates token on handshake<br/>Invalid token → close(4003) immediately

    FeedbackWS->>Broadcaster: register(session_id, ws_client)
    VideoWS->>Orchestrator: start_session(session_id)
    Orchestrator->>Orchestrator: spawn video_task + audio_task

    loop Every ~200ms (browser captures frame)
        Dashboard->>VideoWS: binary frame (JPEG)
        VideoWS->>FrameSvc: enqueue_frame(frame)
        alt Frame is meaningfully different (delta > threshold)
            FrameSvc->>VisionAgent: analyse_frame(frame, session_id)
            VisionAgent->>VisionAPI: POST image for analysis
            VisionAPI-->>VisionAgent: { eye_contact, posture, framing }
            Note over VisionAgent: Builds VideoEventPayload in memory<br/>No DB access from agent
            VisionAgent->>Orchestrator: emit(VideoEventPayload)
            Note over Orchestrator: Pydantic validation wall ✓<br/>Rejects invalid type/severity values
            Orchestrator->>DB: INSERT VideoEvent(type, severity, timestamp_ms)
            Orchestrator->>Broadcaster: publish(session_id, warning_payload)
            Broadcaster->>FeedbackWS: send { type, severity, message, timestamp_ms }
            FeedbackWS-->>Dashboard: warning event
            Dashboard-->>Presenter: 🔴 Toast: "Look at the camera!"
        else Frame is duplicate — drop silently
            FrameSvc->>FrameSvc: discard
        end
    end

    loop Every ~5 seconds (audio chunk)
        Dashboard->>AudioWS: PCM audio chunk
        AudioWS->>AudioAgent: enqueue_chunk(chunk, session_id)
        AudioAgent->>STT: stream audio chunk
        STT-->>AudioAgent: { text, start_ms, end_ms }
        AudioAgent->>AudioAgent: detect_fillers(text) + calc_wpm(rolling_30s)
        Note over AudioAgent: Builds TranscriptPayload + optional<br/>AudioWarningPayload in memory. No DB access.
        AudioAgent->>Orchestrator: emit(TranscriptPayload)
        Orchestrator->>DB: INSERT TranscriptEntry(text, start_ms, end_ms)
        alt Filler word or WPM threshold crossed
            AudioAgent->>Orchestrator: emit(AudioWarningPayload)
            Orchestrator->>Broadcaster: publish(session_id, warning_payload)
            Broadcaster->>FeedbackWS: send { type, severity, message, timestamp_ms }
            FeedbackWS-->>Dashboard: warning event
            Dashboard-->>Presenter: 🔴 Toast: "Speaking too fast!"
        end
    end

    Presenter->>Dashboard: Click "End Session"
    Dashboard->>SessionRouter: POST /sessions/:id/end
    SessionRouter->>Orchestrator: end_session(session_id)
    Orchestrator->>Orchestrator: cancel video_task + audio_task
    Orchestrator->>DB: UPDATE Session(status=ENDED)
    Orchestrator->>Orchestrator: trigger report_task

    Note over Orchestrator,DB: Report generation (async, ≤60s)
    Orchestrator->>ReportAgent: generate(session_id)
    ReportAgent->>DB: READ all VideoEvent, TranscriptEntry, SlideAnalysis
    Note over ReportAgent: Read-only access — safe.<br/>Builds ReportPayload in memory.
    ReportAgent->>ReportAgent: deduplicate_events() — group by type, collect timestamps[]
    ReportAgent->>ReportAgent: calculate_scores() — weighted average
    ReportAgent->>Orchestrator: emit(ReportPayload)
    Note over Orchestrator: Pydantic validation wall ✓<br/>Validates scores are 0-100, insights non-empty
    Orchestrator->>DB: INSERT Report(scores, insights, mentor_unlocked)
    Orchestrator->>DB: UPDATE Session(status=REPORT_READY)
    Orchestrator->>Broadcaster: publish(session_id, { type: REPORT_READY })
    Broadcaster->>FeedbackWS: { type: REPORT_READY }
    FeedbackWS-->>Dashboard: redirect signal
    Dashboard-->>Presenter: Navigate to /session/:id/report
```

---

### 4c. Audio-Only Fallback Activation

```mermaid
sequenceDiagram
    participant FrameSvc as FrameService
    participant VisionAgent
    participant Orchestrator
    participant Dashboard
    participant Presenter

    loop 3 consecutive frames with no response
        FrameSvc->>VisionAgent: analyse_frame(frame)
        Note over VisionAgent: No response within VISION_TIMEOUT_MS (5000ms default)
        VisionAgent--xOrchestrator: timeout
    end

    Orchestrator->>Orchestrator: activate_fallback_mode()
    Orchestrator->>Orchestrator: cancel video_task
    Orchestrator->>Orchestrator: adjust score weights\nVoice 40% + Slides 30% + Content 30%
    Orchestrator->>Broadcaster: publish(session_id,\n{ type: FALLBACK_ACTIVATED })
    Broadcaster-->>Dashboard: fallback event
    Dashboard-->>Presenter: ⚠️ Banner: "Video analysis unavailable\n— continuing with audio coaching"
    Note over Presenter: Session continues normally\nwith audio + slide analysis only
```

---

## 5. Session Isolation — Capability Token Pattern

> **Goal**: One user cannot read, write to, or spy on another user's session — without requiring user accounts or a login flow.

### 5.1 The Problem

Without isolation, any client that learns or guesses a `session_id` can:
- Read the session status and report
- Subscribe to live feedback events via WebSocket
- Upload a malicious PPTX into the session
- Terminate the session

`session_id` UUIDs are hard to guess (128-bit entropy) but this is security by obscurity — not real isolation.

### 5.2 The Pattern: Two-Token Model

```
POST /sessions
  → returns { session_id, access_token }

session_id  — public identifier, safe in URLs and logs
access_token — secret capability, stored in localStorage, NEVER in URLs
```

Every protected operation requires **both**:
- HTTP: `Authorization: Bearer <access_token>` header
- WebSocket: `?session_id=X&token=<access_token>` query param
- Report share link (opt-in): `?share=<share_token>` — separate read-only token

### 5.3 Token Lifecycle

```
[Browser]                          [Backend]
  |                                    |
  | POST /sessions                     |
  |----------------------------------->|
  |                                    | INSERT sessions(session_id, access_token)
  |<-----------------------------------|
  | { session_id, access_token }       |
  |                                    |
  | localStorage.set("token_X", token) |  ← stored per session_id key
  |                                    |
  | All subsequent requests include    |
  | Authorization: Bearer <token>      |
  |                                    |
  | GET /sessions/:id/report           |
  | Authorization: Bearer <token>  --->|
  |                                    | SELECT * FROM sessions
  |                                    | WHERE session_id=$1
  |                                    |   AND access_token=$2
  |                                    | → match → 200 OK
  |                                    | → no match → 403 Forbidden
```

### 5.4 What Each Token Grants

| Token | Stored in | Grants | Scope |
|---|---|---|---|
| `access_token` | Browser `localStorage` | Full read + write on own session | Created once at `POST /sessions` |
| `share_token` | Report URL query param (opt-in) | Read-only access to the report page only | Generated on demand via `POST /sessions/:id/report/share` |

**Share link flow:**
1. Owner (with `access_token`) clicks "Copy share link"
2. Frontend calls `POST /sessions/:id/report/share` (requires `access_token`)
3. Backend generates `share_token`, stores on `reports` table
4. Returns shareable URL: `/session/:id/report?share=<share_token>`
5. Anyone with that URL can view the report — no `access_token` needed
6. `share_token` grants zero write access — cannot end session, cannot upload

### 5.5 Protected Routes (complete list)

| Route | Method | Token required | Notes |
|---|---|---|---|
| `POST /sessions` | Create | None | Returns both tokens |
| `GET /sessions/:id` | Read status | `access_token` | Owner only |
| `POST /sessions/:id/upload` | Upload PPTX | `access_token` | Owner only |
| `POST /sessions/:id/end` | End session | `access_token` | Owner only |
| `GET /sessions/:id/report` | View report | `access_token` OR `share_token` | Owner or share recipient |
| `POST /sessions/:id/report/share` | Generate share link | `access_token` | Owner only |
| `ws://…/video-stream?session_id=X&token=Y` | Live video | `access_token` | Owner only |
| `ws://…/audio-stream?session_id=X&token=Y` | Live audio | `access_token` | Owner only |
| `ws://…/realtime-feedback?session_id=X&token=Y` | Live events | `access_token` | Owner only |

### 5.6 FastAPI Middleware Implementation

```python
# middleware/session_auth.py

from fastapi import Depends, HTTPException, Header, status
from db.repository import PostgreSQLRepository

async def require_session_owner(
    session_id: str,
    authorization: str = Header(...),
    repo: PostgreSQLRepository = Depends(get_repo),
):
    """
    Dependency injected into all protected routes.
    Validates that the access_token in the Authorization header
    matches the token stored for this session_id.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    access_token = authorization.removeprefix("Bearer ").strip()
    session = await repo.get_session(session_id)

    if not session or session.access_token != access_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired session token"
        )
    return session


async def require_report_access(
    session_id: str,
    authorization: str = Header(default=""),
    share: str | None = None,
    repo: PostgreSQLRepository = Depends(get_repo),
):
    """
    Report-specific dependency: accepts either the owner access_token
    OR a valid share_token query param.
    """
    # Try access_token first
    if authorization.startswith("Bearer "):
        access_token = authorization.removeprefix("Bearer ").strip()
        session = await repo.get_session(session_id)
        if session and session.access_token == access_token:
            return session

    # Fall back to share_token
    if share:
        report = await repo.get_report_by_session(session_id)
        if report and report.share_token == share:
            return report

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


# WebSocket token validation (used in ws route handlers)
async def validate_ws_token(session_id: str, token: str, repo) -> bool:
    session = await repo.get_session(session_id)
    return session is not None and session.access_token == token
```

### 5.7 DB Schema Changes

```sql
-- Add access_token to sessions table
ALTER TABLE sessions ADD COLUMN access_token UUID NOT NULL DEFAULT gen_random_uuid();
CREATE INDEX idx_sessions_token ON sessions(session_id, access_token);

-- Add share_token to reports table (nullable — only set when owner generates a share link)
ALTER TABLE reports ADD COLUMN share_token UUID;
CREATE INDEX idx_reports_share_token ON reports(share_token) WHERE share_token IS NOT NULL;
```

### 5.8 Frontend Responsibilities (Dev 6)

```typescript
// On session create — store token keyed by session_id
const { session_id, access_token } = await POST("/sessions");
localStorage.setItem(`token_${session_id}`, access_token);

// On all subsequent requests — retrieve and attach
const token = localStorage.getItem(`token_${session_id}`);
fetch(`/sessions/${session_id}/upload`, {
  headers: { Authorization: `Bearer ${token}` }
});

// WebSocket connections — include token in query param
const ws = new WebSocket(
  `wss://backend/realtime-feedback?session_id=${session_id}&token=${token}`
);

// Share link generation
const { share_url } = await POST(`/sessions/${session_id}/report/share`, {
  headers: { Authorization: `Bearer ${token}` }
});
// share_url = "/session/:id/report?share=<share_token>"
navigator.clipboard.writeText(share_url);
```

---

## 5b. Agent Specifications — Memory / Model / Tools

> Each agent has a clear contract. Developers own the implementation — this table defines what goes in and what comes out. Agents never write to the DB directly; they emit a typed payload to the Orchestrator.

| Agent | Phase | Memory (context it holds) | Model / Service | Tools / Actions | Emits to Orchestrator |
|---|---|---|---|---|---|
| **Frame Service** | P1 infra | Last N frames for delta comparison | None (algorithmic) — uses **`imagehash` (dhash)** [`pip install imagehash Pillow`] | `imagehash.dhash(frame)` → compare Hamming distance against threshold (default: 8). Drop frame if distance ≤ threshold. | Filtered frame stream → Vision Agent |
| **Audio Agent** | P1 | Rolling transcript buffer, WPM window (30s) | ElevenLabs Scribe v1 (STT) | `transcribe(chunk)`, `detect_fillers(text)`, `calc_wpm()` | `TranscriptPayload`, `AudioWarningPayload` |
| **Vision Agent** | P2 | Session ID, last event type (to avoid duplicate events), rolling buffer of last 3 frames | GPT-4o Vision via Tikal LiteLLM (`https://litelm.tikalk.dev/v1`) — multimodal; evaluates posture, eye contact, framing, gestures from frame batch | `analyse_frames(image[])` — batched call every 600ms (3 frames @ 5fps) | `VideoEventPayload` |
| **PPTX Agent** | P1 | Slide content extracted from file, Playbook 12 factors | Tikal LiteLLM (`https://litelm.tikalk.dev/v1`) — personal API key per dev | `parse_pptx(file)`, `evaluate_slide(content, factors)` | `SlideAnalysisPayload[]` |
| **Content Agent** | P2 | Full session transcript, session topic | Tikal LiteLLM (`https://litelm.tikalk.dev/v1`) — personal API key per dev | `read_transcript(session_id)`, `evaluate_accuracy(transcript, topic)` | `ContentAnalysisPayload` |
| **Report Agent** | P1 basic / P2 full | All events for the session from DB | Tikal LiteLLM (`https://litelm.tikalk.dev/v1`) — personal API key per dev | `read_all_events(session_id)`, `deduplicate()`, `score()` | `ReportPayload` |

---

## 5c. User-Facing Output — What the Presenter Sees

### Phase 1 Report (minimum viable output)

```
SESSION REPORT — "My React Talk" — June 24, 2026

🗣️ VOICE & DELIVERY
  ⚠️  Filler words: Said "um" / "ahh" 18 times total
       → See: 0:42, 1:15, 2:40, 3:05, 4:22 ...
  ⚠️  Pacing: Speaking too fast (avg 175 WPM)
       → See: 1:30–2:10, 3:40–4:05
  ✅  Strong energy variation in the opening 2 minutes

🖼️ SLIDE QUALITY
  ⚠️  Slide 3: Too much text — violates Factor #4 (Keep it visual)
  ⚠️  Slide 7: No visual anchor — violates Factor #6 (Use imagery)
  ✅  Slide 1: Clean title, strong contrast — good first impression
```

### Phase 2 Report (full 4-vector scorecard)

```
OVERALL SCORE: 74 / 100
🔒 You are 6 points away from unlocking a 1-on-1 with a Tikal Expert

🗣️ Voice & Delivery    — 68/100
🎥 Body Language        — 71/100
🖼️ Slide Quality        — 82/100
🧠 Technical Accuracy   — 75/100

[Each section: Strengths ✅ + Improvements ⚠️ with timestamps/slide refs]
[Content section also shows: topic evaluated, disclaimer about AI cutoff]
```

---

## 6. Technology Stack

| Layer | Technology | Version | Rationale |
|---|---|---|---|
| Frontend framework | TanStack Start | Latest | SSR/SPA hybrid, file-based routing, hackathon eval multiplier |
| Frontend type layer | Spec it | Latest | Type-safe specs, hackathon eval multiplier |
| Backend framework | FastAPI | 0.111+ | Native async WebSocket, Python ecosystem for AI libs |
| Agent orchestration | Agno | Latest | Required by spec; manages agent lifecycle + shared async state |
| Vision AI | GPT-4o Vision via Tikal LiteLLM | — | Multimodal LLM evaluates posture, eye contact, framing, gestures. Batched 3 frames/call @ 5fps source → ~1000 calls per 10-min session. Routed through LiteLLM gateway, no separate IT key. |
| LLM (PPTX, Content, Report agents) | Tikal LiteLLM | `https://litelm.tikalk.dev/v1` | Internal AI gateway — routes to OpenAI / Claude / Gemini. Each dev uses their own personal API key ($20 budget each). |
| STT provider | ElevenLabs Scribe v1 | — | Streaming transcription; API key provided by IT |
| PPTX parsing | python-pptx | 0.6+ | Standard Python PPTX library, zero cost |
| ORM | SQLAlchemy (async) | 2.x | Async-native, works with FastAPI/asyncpg |
| DB driver | asyncpg | Latest | Async PostgreSQL driver |
| Database | PostgreSQL 15 | Railway managed | Native Railway plugin, one-click |
| Package manager (root) | pnpm workspaces | 9+ | Monorepo management across Python + JS packages |
| Python env manager | uv | Latest | Fast Python dep management per backend package |
| Hosting | Railway | — | Pre-configured pipeline, zero-ops for hackathon |
| CI/CD | Railway auto-deploy | — | Push to `main` → auto-deploy all services |

---

## 6. Data Architecture

### Entity Relationship (High Level)

```
Session (1) ──────────────── (many) TranscriptEntry
Session (1) ──────────────── (many) VideoEvent
Session (1) ──────────────── (many) SlideAnalysis
Session (1) ──────────────── (1)    Report
Report  (1) ──────────────── (many) Insight  [embedded JSON array]
```

### Schema Summary

```sql
-- Session
CREATE TABLE sessions (
    session_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    access_token UUID NOT NULL DEFAULT gen_random_uuid(),  -- capability token for isolation
    topic        TEXT NOT NULL,                            -- required: "React 19 new features"
    topic_context TEXT,                                    -- optional: audience level, version info
    status       TEXT NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE | ENDED | REPORT_READY
    pptx_ready   BOOLEAN DEFAULT false,
    slides_raw_text JSONB,   -- [{slide_index, text}] persisted by PPTXAgent before LLM call; survives container restart
    started_at   TIMESTAMPTZ DEFAULT now(),
    ended_at     TIMESTAMPTZ
);
CREATE INDEX idx_sessions_token ON sessions(session_id, access_token);

-- TranscriptEntry (written by AudioAgent in real time)
CREATE TABLE transcript_entries (
    id           SERIAL PRIMARY KEY,
    session_id   UUID REFERENCES sessions(session_id),
    start_ms     INTEGER NOT NULL,
    end_ms       INTEGER NOT NULL,
    text         TEXT NOT NULL,
    filler_flags TEXT[]  -- ['um', 'like']
);

-- VideoEvent (written by VisionAgent in real time)
CREATE TABLE video_events (
    id           SERIAL PRIMARY KEY,
    session_id   UUID REFERENCES sessions(session_id),
    timestamp_ms INTEGER NOT NULL,
    event_type   TEXT NOT NULL,  -- EYE_CONTACT_LOST | POSTURE_ISSUE | OUT_OF_FRAME
    severity     TEXT NOT NULL,  -- LOW | MEDIUM | HIGH
    raw_metadata JSONB
);

-- SlideAnalysis (written by PPTXAgent on upload)
CREATE TABLE slide_analyses (
    id              SERIAL PRIMARY KEY,
    session_id      UUID REFERENCES sessions(session_id),
    slide_index     INTEGER NOT NULL,
    playbook_factor INTEGER NOT NULL,  -- 1-12
    finding_type    TEXT NOT NULL,     -- STRENGTH | IMPROVEMENT
    description     TEXT NOT NULL
);

-- Report (written by ReportAgent after session ends)
CREATE TABLE reports (
    id               SERIAL PRIMARY KEY,
    session_id       UUID REFERENCES sessions(session_id) UNIQUE,
    overall_score    NUMERIC(5,2),
    voice_score      NUMERIC(5,2),
    body_score       NUMERIC(5,2),
    slide_score      NUMERIC(5,2),
    content_score    NUMERIC(5,2),   -- replaces sync_score
    insights         JSONB,   -- serialised Insight[] array
    mentor_unlocked  BOOLEAN DEFAULT false,
    generated_at     TIMESTAMPTZ DEFAULT now(),
    share_token      UUID     -- NULL until owner generates a share link
);
CREATE INDEX idx_reports_share_token ON reports(share_token) WHERE share_token IS NOT NULL;
```

### Insight JSON shape (embedded in `reports.insights`)

```json
{
  "category": "voice",
  "type": "IMPROVEMENT",
  "message": "You used 'um' / 'like' excessively (24 times total). Try to pause instead.",
  "timestamps": [72000, 225000, 442000],
  "slides": []
}
```

### Write patterns

| Writer | Table | Frequency |
|---|---|---|
| AudioAgent | `transcript_entries` | Every ~5 s during session |
| VisionAgent | `video_events` | Every detected event (~0.2–2 s) |
| PPTXAgent | `slide_analyses` | Once on upload (batch) |
| ReportAgent | `reports` | Once on session end |
| SessionManager | `sessions` | On create + status transitions |

---

## 7. WebSocket Contract (Full Spec)

### Inbound (browser → backend)

| Route | Message format | Auth | Notes |
|---|---|---|---|
| `ws://backend/video-stream?session_id=X&token=Y` | Binary (JPEG frame) | `access_token` required | Rejected with 403 on handshake if token invalid |
| `ws://backend/audio-stream?session_id=X&token=Y` | Binary (PCM 16-bit, 16kHz) | `access_token` required | Rejected with 403 on handshake if token invalid |

### Outbound (backend → browser)

| Route | Message format | Auth | Publisher |
|---|---|---|---|
| `ws://backend/realtime-feedback?session_id=X&token=Y` | JSON (see below) | `access_token` required | FeedbackBroadcaster |

> **WebSocket token validation** happens during the HTTP upgrade handshake — before the connection is established. An invalid token closes the connection immediately with code 4003 (application-level 403). This prevents any unauthorised client from subscribing to another user's live event stream.

> **Token in query param — accepted trade-off**: WebSocket browsers can't send custom Authorization headers, so `?token=` is required. Token is logged in reverse-proxy access logs. Mitigation: tokens are session-scoped (expire on session END), never reused across sessions, and rotated on report-share generation.

> **Browser reconnect**: All 3 WS connections use exponential-backoff reconnect (1s, 2s, 4s, 8s cap) — see §10b.3. `session_id` + `access_token` persist in `localStorage` so reconnect rebinds to the same session.

```json
// Warning event (during session)
{
  "type": "EYE_CONTACT_LOST",
  "severity": "HIGH",
  "message": "Look back at the camera",
  "timestamp_ms": 142500
}

// Report ready signal (after session ends)
{
  "type": "REPORT_READY",
  "session_id": "uuid-xxxx"
}

// Fallback activated signal
{
  "type": "FALLBACK_ACTIVATED",
  "message": "Video analysis unavailable — continuing with audio coaching"
}
```

---

## 8. Infrastructure & Deployment `[Phase 3 — Optional]`

> **For the hackathon demo, everything runs locally. No deployment is required.** Railway deployment is a Phase 3 bonus — only if the team finishes Phases 1 and 2 with time to spare.

```
Railway Project: octoprep2000
│
├── Service: backend          (Python FastAPI — all agents)
│   ├── Build: Dockerfile or nixpacks
│   ├── Start: uvicorn main:app --host 0.0.0.0 --port $PORT
│   ├── Health: GET /health → 200 OK
│   └── Env vars:
│       ELEVENLABS_API_KEY=...            (ElevenLabs Scribe v1 — STT)
│       LITELLM_API_KEY=...              (Tikal LiteLLM personal key — per dev; covers Vision + PPTX + Content + Report)
│       LITELLM_BASE_URL=https://litelm.tikalk.dev/v1
│       LITELLM_VISION_MODEL=gpt-4o       (multimodal model for VisionAgent)
│       DATABASE_URL=postgresql+asyncpg://...  (injected by Railway Postgres plugin)
│       VISION_TIMEOUT_MS=5000
│       MENTOR_BOOKING_URL=https://calendly.com/...
│       DEMO_MODE=                         (set to "replay" only if live APIs flake during demo)
│       RATE_LIMIT_SESSIONS_PER_MIN=5
│
├── Service: web-dashboard    (TanStack Start — Node/Bun)
│   ├── Build: pnpm build
│   ├── Start: node .output/server/index.mjs
│   └── Env vars:
│       VITE_BACKEND_URL=https://backend.railway.app
│       VITE_WS_URL=wss://backend.railway.app
│
└── Plugin: PostgreSQL 15
    └── DATABASE_URL auto-injected into backend service
```

**Keep-warm strategy**: Railway's built-in health check pings `GET /health` every 30s. Set Railway's restart policy to "Never" on health check failure during demo hours to avoid cold starts.

**Environment layout:**

| Environment | Branch | Purpose |
|---|---|---|
| Production | `main` | Live demo — Railway auto-deploys on push |
| Local dev | — | Each dev runs their service locally with `.env` |

> No staging environment for the hackathon — one environment, one branch, keep it simple.

---

## 9. Monorepo Structure

```
octoprep2000/                     ← pnpm workspace root
│
├── package.json                  ← workspace: ["packages/*"]
├── pnpm-workspace.yaml
├── .env.example                  ← all required keys, no values
│
├── packages/
│   ├── web-dashboard/            ← Dev 6 (TanStack Start, TypeScript)
│   │   ├── package.json
│   │   ├── app/
│   │   │   ├── routes/
│   │   │   │   ├── index.tsx         ← landing / session setup
│   │   │   │   ├── session.$id.tsx   ← live session view (toasts + camera)
│   │   │   │   └── session.$id.report.tsx ← scorecard
│   │   │   └── components/
│   │   └── ...
│   │
│   ├── backend/                  ← Single FastAPI service (all agents live here)
│   │   ├── pyproject.toml        ← uv / poetry managed
│   │   ├── main.py               ← FastAPI app, router registration
│   │   ├── routers/
│   │   │   ├── health.py         ← GET /health (Railway keep-warm)
│   │   │   ├── sessions.py       ← POST /sessions (rate-limited), POST /sessions/:id/end
│   │   │   ├── upload.py         ← POST /sessions/:id/upload
│   │   │   ├── video_ws.py       ← ws://backend/video-stream
│   │   │   ├── audio_ws.py       ← ws://backend/audio-stream
│   │   │   └── feedback_ws.py    ← ws://backend/realtime-feedback
│   │   ├── middleware/
│   │   │   └── session_auth.py       ← require_session_owner + require_report_access + validate_ws_token
│   │   ├── core/
│   │   │   ├── session_manager.py
│   │   │   └── feedback_broadcaster.py
│   │   ├── orchestrator/
│   │   │   └── orchestrator.py
│   │   ├── agents/
│   │   │   ├── schemas.py            ← ALL typed Pydantic payloads (only contract agents expose)
│   │   │   ├── frame_service.py      ← non-agent utility, no DB access
│   │   │   ├── vision_agent.py       ← emits VideoEventPayload only
│   │   │   ├── audio_agent.py        ← emits TranscriptPayload + AudioWarningPayload only
│   │   │   ├── pptx_agent.py         ← emits SlideAnalysisPayload[] only
│   │   │   ├── content_agent.py      ← reads transcript from DB, calls LLM, emits ContentAnalysisPayload (Dev 3)
│   │   │   ├── replay_fixtures.py    ← DEMO_MODE=replay canned events (Vision + Audio)
│   │   │   └── report_agent.py       ← reads DB (read-only), emits ReportPayload (4 vectors)
│   │   ├── db/
│   │   │   ├── models.py         ← SQLAlchemy models
│   │   │   └── repository.py     ← async CRUD
│   │   └── migrations/           ← Alembic
│   │
│   └── shared-types/             ← optional: shared TypeScript types for WS payloads
│       └── package.json
│
└── docs/                         ← all MD documents live here
    ├── MASTER-DOCUMENT.md
    ├── PRD.md
    ├── PRESENTATION-SKILLS-PLAYBOOK.md
    ├── TEAM-LEAD-CHECKLIST.md
    └── TECH-ARCHITECTURE-C4.md   ← this file
```

---

## 10. Risks & Trade-offs

| Decision | Alternative Considered | Why Chosen | Risk | Mitigation |
|---|---|---|---|---|
| Single FastAPI process | True microservices | 6-hour build constraint; no inter-service networking to debug | One agent's blocking call stalls all agents | Use `asyncio.run_in_executor` for any blocking I/O; never block the event loop |
| In-process asyncio pub/sub | Redis pub/sub | No extra Railway service; simpler code | Doesn't scale beyond single instance | Acceptable: hackathon is single-node; pub/sub in `FeedbackBroadcaster` is a clean interface that can be swapped to Redis post-hackathon |
| Temp file PPTX (/tmp) + raw text persisted to DB | Railway volume / S3 | Zero setup, zero cost | File lost on container restart | **v1.3**: extracted slide text persisted to `sessions.slides_raw_text` JSONB **before** LLM call — restart survives, agent resumes from DB. PPTX binary still discarded after parse. |
| No auth layer | JWT / session tokens | No user accounts in scope for MVP | Any client with a `session_id` UUID can connect to that session | UUIDs are unpredictable (128-bit entropy); acceptable for a demo |
| Orchestrator as sole DB writer | Agents write to DB directly | Centralises validation; agents are pure AI logic with no DB coupling | Orchestrator `on_event` becomes a bottleneck if event volume is very high | **v1.3**: Frame service rate-limits to ≤5fps. VideoEvent inserts batched (every 1s OR N=20) — see §10b.5. AudioAgent chunks 2s. Warning broadcast is sync (immediate); DB write is the only batched step. |
| Session capability tokens (no user accounts) | Full JWT auth with user table | No login flow needed, zero friction for demo, full session isolation | Token lives in localStorage — lost if browser data cleared (user must start a new session) | Acceptable for hackathon. Post-hackathon: migrate to proper JWT with refresh tokens. |
| Report protected by default; opt-in share_token | Report fully public by URL | Prevents one user reading another's scorecard; explicit sharing is opt-in and intentional | Adds one extra API call (`POST .../report/share`) to generate a share link | Simple endpoint, ~30 min to implement. Worth it for data integrity. |
| Single Railway environment | Dev + Staging + Prod | Reduces ops overhead during hackathon | A bad push to `main` breaks the demo | Keep `main` protected; manual approval for pushes after Sprint 2 integration is working |
| PostgreSQL (no Redis) | PostgreSQL + Redis | Railway Postgres plugin is one click; no extra service | Report generation reads all rows — could be slow for long sessions | Sessions are demo-length (5–10 min max); read performance is not a concern at this scale |

---

## 10b. Demo-Day Hardening (v1.3)

> Added in v1.3 to close demo-failure risks identified in architecture critique.

### 10b.1 Health endpoint

```python
# routers/health.py
from fastapi import APIRouter
router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}
```

Railway keep-warm pings `GET /health` every 30s. Endpoint is unauthenticated, no DB call, no LLM call — pure liveness signal.

### 10b.2 DEMO_MODE replay

`DEMO_MODE=replay` env flag swaps live Vision/STT calls for canned JSON event fixtures. Demo-day insurance if Google/ElevenLabs/LiteLLM flake.

```python
# In VisionAgent + AudioAgent
if os.getenv("DEMO_MODE") == "replay":
    return replay_fixture(session_id)
```

Fixtures live in `backend/fixtures/{vision,audio}_events.json`. Dev5 owns. Team Lead toggles flag at demo time only if real APIs are down.

### 10b.3 WebSocket reconnect (browser)

```typescript
// app/lib/ws.ts — applied to all 3 WS connections
function connectWithRetry(url: string, onMessage: (e: MessageEvent) => void) {
  let attempt = 0;
  const open = () => {
    const ws = new WebSocket(url);
    ws.onmessage = onMessage;
    ws.onclose = () => {
      attempt++;
      const delay = Math.min(1000 * 2 ** attempt, 8000);
      setTimeout(open, delay);
    };
    ws.onopen = () => { attempt = 0; };
  };
  open();
}
```

Exponential backoff capped at 8s. Session state survives 1 reconnect because `session_id` + `access_token` in localStorage.

### 10b.4 Rate limiting

`POST /sessions` rate-limited via `slowapi` — 5 requests / minute / IP. Prevents demo URL DoS.

```python
# main.py
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.post("/sessions")
@limiter.limit("5/minute")
async def create_session(...): ...
```

### 10b.5 VideoEvent batched inserts

Orchestrator buffers `VideoEvent` payloads and flushes every 1s OR at N=20:

```python
class Orchestrator:
    def __init__(self):
        self._video_event_buffer: list[VideoEvent] = []

    async def on_video_event(self, ev: VideoEventPayload):
        self._video_event_buffer.append(ev)
        if len(self._video_event_buffer) >= 20:
            await self._flush_video_events()

    async def _flush_video_events(self):
        if not self._video_event_buffer: return
        await self.repo.bulk_insert_video_events(self._video_event_buffer)
        self._video_event_buffer.clear()

    # Background task flushes every 1s in case buffer doesn't fill
```

Warnings still broadcast to FeedbackWS immediately — only DB write is batched.

### 10b.6 PPTX raw text persisted

`PPTXAgent` writes extracted slide text to `slides.raw_text` JSONB column on parse, before LLM evaluation. If container restarts mid-analysis, agent resumes from DB instead of `/tmp` file.

```sql
ALTER TABLE sessions ADD COLUMN slides_raw_text JSONB;  -- [{slide_index, text}]
```

### 10b.7 Topic validation

`POST /sessions` body validation via Pydantic:

```python
class CreateSessionBody(BaseModel):
    topic: str = Field(min_length=8, max_length=200)
    topic_context: str | None = Field(default=None, max_length=500)

    @field_validator("topic")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("topic cannot be blank")
        return v
```

Optional LLM sanity check (`is_valid_technical_topic`) deferred to Phase 2 polish.

### 10b.8 Browser frame capture

Capture pipeline: `getUserMedia` → `OffscreenCanvas` (320×240) → JPEG @ quality 0.7 → WS binary frame.
Capture cadence: every 200ms (5fps source). Downscale **before** encode to keep main thread free.

```typescript
const offscreen = new OffscreenCanvas(320, 240);
const ctx = offscreen.getContext("2d")!;
setInterval(async () => {
  ctx.drawImage(video, 0, 0, 320, 240);
  const blob = await offscreen.convertToBlob({ type: "image/jpeg", quality: 0.7 });
  ws.send(await blob.arrayBuffer());
}, 200);
```

---

## 11. Open Architecture Decisions

> Items that are still TBD and must be resolved before June 24.

| # | Decision | Owner | Options | Due |
|---|---|---|---|---|
| 1 | ~~Vision API choice~~ | Dev 1 | ✅ **Decided (v1.3): GPT-4o Vision via Tikal LiteLLM** — multimodal model evaluates posture, eye contact, framing, gestures (Google Cloud Vision dropped — only did face landmarks, no body language). Batched 3 frames per call to amortise tokens. Uses existing LiteLLM gateway — no separate IT key. | ~~June 20~~ **Done** |
| 2 | ~~STT provider choice~~ | Dev 2 | ✅ **Decided: ElevenLabs Scribe v1** — API key provided by IT. | ~~June 20~~ **Done** |
| 3 | ~~Frame delta library~~ | Dev 1 | ✅ **Decided: `imagehash` (dhash)**. `pip install imagehash Pillow`. Hamming distance threshold = 8 (tune up to drop more frames, down to keep more). Fallback: OpenCV `absdiff` if more control is needed. | ~~June 20~~ **Done** |
| 4 | Agno session task model | Dev 5 | **PoC by June 20**: confirm Agno async model handles 3 concurrent WS streams without blocking. **Fallback path (locked in advance)**: raw `asyncio.create_task` per session — Agno is brand-tax, not load-bearing. If PoC fails, drop Agno entirely; agents become plain async coroutines, Orchestrator stays. | June 20 |
| 5 | Audio format + chunk size | Dev 2 | ✅ **Decided (v1.3)**: PCM 16-bit 16kHz, **2-second chunks** (down from 5s) to meet NFR-002 ≤1s filler latency. WebM Opus considered — rejected (encode overhead in browser). | ~~June 20~~ **Done** |
| 6 | TanStack Start: SSR vs. SPA | Dev 6 | Full SSR adds complexity; SPA mode is simpler for a WS-heavy app | June 14 |
| 7 | DB migrations strategy | Dev 5 | Alembic auto-generate on startup vs. hand-written migration scripts | June 14 |

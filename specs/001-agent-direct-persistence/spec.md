# Feature Specification: Agent-Owned Persistence (Direct-to-Agent Data Flow)

**Feature Branch**: `001-agent-direct-persistence`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "Currently the data inputs (video, audio, etc.) go to the orchestrator. We want to change that: the data will be sent directly to the agents respecting their role, then they process it and put it on the DB and notify that they finished processing. The orchestrator will take the data from the agreed place. Make sure you update all needed, also docs and presentations."

## Overview

Today the Orchestrator is the single hub: agents emit typed payloads to it, and the
Orchestrator alone validates and writes them to PostgreSQL, then composes the report.

This feature inverts persistence ownership. Each input (video frames, audio chunks,
PPTX deck) is delivered straight to the agent that owns that input type. That agent
processes it, **writes its own results to the database** at an agreed, documented
location, and **emits a completion signal**. The Orchestrator stops relaying raw input
payloads; instead it reads finished results from the agreed database location and
assembles the scored report at `/session/:id/report`.

> **GOVERNANCE IMPACT (must resolve before `/spec-plan`)**: This change directly
> contradicts Constitution Principle II "Contracted Agent Boundaries", which states the
> Orchestrator MUST own all writes to PostgreSQL and agents MUST NOT bypass it for
> writes. Adopting this feature requires an explicit constitution amendment (or a scoped
> exception) re-defining the persistence-ownership boundary. See FR-013 and the
> Dependencies section.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agents persist their own live-capture results (Priority: P1)

A presenter records a live rehearsal. Video frames flow to the Vision agent and audio
chunks flow to the Audio agent. Each agent processes its stream and writes its own
results (video events, transcript entries, audio warnings) directly to the database as
they are produced. The presenter still sees real-time feedback and, at session end, a
complete report — with no observable difference from today's behavior.

**Why this priority**: This is the core of the requested change and covers the
highest-volume, highest-risk live paths. Without it the feature delivers nothing.

**Independent Test**: Run a rehearsal in `DEMO_MODE=replay`; confirm video events,
transcript entries, and audio warnings appear in the database written by their owning
agents (not the Orchestrator), and the live feedback stream and final report match the
pre-change baseline.

**Acceptance Scenarios**:

1. **Given** an active session, **When** video frames reach the Vision agent, **Then**
   the Vision agent writes its video events to the agreed database location and the
   Orchestrator performs no write for those events.
2. **Given** an active session, **When** audio chunks reach the Audio agent, **Then** the
   Audio agent writes transcript entries and any audio warnings directly to the database.
3. **Given** real-time feedback subscribers, **When** an agent persists a noteworthy
   event, **Then** subscribers still receive the live feedback event with no added
   user-visible latency regression beyond the existing batching window.

### User Story 2 - Agents signal completion and the Orchestrator reads from the agreed place (Priority: P1)

When an agent finishes a unit of processing (a flushed batch of live events, a completed
deck analysis, a finished post-session pass), it emits a "processing finished"
notification. The Orchestrator no longer receives raw payloads to persist; it observes
these completion signals and reads the finished data from the agreed database location to
drive session-state transitions and report assembly.

**Why this priority**: The completion contract is what lets the Orchestrator know when
data is safe to read. Report assembly is impossible without a reliable "done" signal.

**Independent Test**: Trigger each agent's processing; confirm a completion signal is
emitted per agent, and the Orchestrator advances session state / assembles the report by
reading the agreed database location rather than from in-memory payloads passed by agents.

**Acceptance Scenarios**:

1. **Given** an agent has written its results, **When** it finishes, **Then** it emits a
   completion notification identifying the session and the kind of work completed.
2. **Given** all required agents have signaled completion for a session, **When** the
   session ends, **Then** the Orchestrator assembles the report by reading the agreed
   database location and marks the session REPORT_READY.
3. **Given** the Orchestrator, **When** it composes the report, **Then** it does not
   depend on having received raw input payloads from the agents.

### User Story 3 - PPTX deck is persisted by its owning agent (Priority: P2)

A presenter uploads a PPTX deck. The deck is handed directly to the PPTX agent, which
extracts and persists raw slide text and its findings to the database itself, then signals
completion. The frontend's existing readiness polling continues to report `pptx_ready`
once persistence is done.

**Why this priority**: The PPTX path is lower-volume and asynchronous, but must follow
the same ownership model for consistency and to keep the report inputs uniform.

**Independent Test**: Upload a deck; confirm slide analyses and raw slide text are written
by the PPTX agent, a completion signal fires, and `GET /sessions/:id` reports
`pptx_ready=true`.

**Acceptance Scenarios**:

1. **Given** an uploaded deck, **When** the PPTX agent finishes analysis, **Then** it has
   written slide analyses and raw slide text to the database itself and emitted completion.
2. **Given** a completed deck analysis, **When** the frontend polls session status,
   **Then** `pptx_ready` reflects the agent's own persistence, not an Orchestrator write.

### User Story 4 - Documentation and presentation reflect the new flow (Priority: P2)

The architecture documentation and the kickoff architecture presentation are updated so
that the described data flow matches the implemented behavior: inputs go directly to
agents, agents own persistence and signal completion, and the Orchestrator reads from the
agreed location.

**Why this priority**: The user explicitly required docs and the presentation be updated.
A flow diagram that contradicts the running system misleads the team and the demo audience.

**Independent Test**: Review `docs/TECH-ARCHITECTURE-C4.md` and
`docs/presentation/ARCHITECTURE-DECK.html`; confirm every data-flow description, sequence
diagram, and "Orchestrator is sole writer" statement is updated to the new model with no
lingering references to the old flow.

**Acceptance Scenarios**:

1. **Given** the updated architecture doc, **When** a reader follows the live-session and
   PPTX sequence flows, **Then** they describe direct-to-agent delivery, agent-owned
   writes, and completion signals.
2. **Given** the kickoff architecture presentation, **When** the architecture slide(s) are
   shown, **Then** the diagram and narration match the new flow.

### Edge Cases

- What happens when an agent writes partial results, then crashes before emitting
  completion? The Orchestrator MUST NOT treat the session as fully processed; the report
  path MUST degrade safely (existing audio-only / fallback behavior preserved).
- What happens when two agents write concurrently for the same session? Each agent owns a
  distinct data kind, so writes MUST NOT race on the same rows; ordering of independent
  kinds is not required.
- What happens when a completion signal is lost or arrives before the corresponding write
  is durable? The Orchestrator MUST read only durably-committed data and MUST have a
  bounded wait / timeout before proceeding or falling back.
- What happens to high-volume video events that were previously batched by the
  Orchestrator (flush every 1s or at N=20)? Equivalent batching MUST be preserved at the
  agent that now owns the write, to protect database write volume.
- What happens in `DEMO_MODE=replay`? The new ownership and completion flow MUST work
  unchanged with canned fixtures.
- What happens on Vision-timeout fallback (3 consecutive timeouts → audio-only)? The
  fallback trigger and score reweighting MUST still function under agent-owned writes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each presentation input type MUST be delivered directly to the agent that
  owns that input role (video → Vision agent, audio → Audio agent, PPTX → PPTX agent)
  rather than being relayed through the Orchestrator as a data pipe.
- **FR-002**: Each owning agent MUST write the results it produces directly to the
  database (video events, transcript entries, audio warnings, slide analyses + raw slide
  text, and post-session content/report outputs as applicable).
- **FR-003**: The Orchestrator MUST NOT perform the persistence writes for data that an
  agent now owns; its role for those data kinds becomes coordination and reading.
- **FR-004**: Each agent MUST emit a "processing finished" notification when it completes
  a unit of work, identifying at minimum the session and the kind of work completed.
- **FR-005**: The Orchestrator MUST obtain processed data by reading from the agreed,
  documented database location, not from raw input payloads passed by agents.
- **FR-006**: The agreed database location/schema for each data kind MUST be explicit and
  documented so agents (writers) and the Orchestrator (reader) share one contract.
- **FR-007**: The Orchestrator MUST be able to determine, per session, whether all
  required agents have completed, and MUST drive session-state transitions (ACTIVE →
  ENDED → REPORT_READY) and report assembly based on completion signals plus the agreed
  data.
- **FR-008**: Real-time feedback to subscribers MUST be preserved; noteworthy events MUST
  still reach the live feedback stream with no user-visible latency regression beyond the
  existing batching window.
- **FR-009**: High-volume write batching previously performed by the Orchestrator MUST be
  preserved at the owning agent to protect database write volume.
- **FR-010**: The feature MUST preserve existing resilience behavior: audio-only fallback
  on repeated Vision timeouts, bounded external-call latency, graceful degradation on
  agent crash or lost completion signal, and `DEMO_MODE=replay`.
- **FR-011**: The end-to-end demo path (upload PPTX → rehearse → end session →
  `/session/:id/report`) MUST produce output equivalent to the pre-change baseline.
- **FR-012**: Documentation (`docs/TECH-ARCHITECTURE-C4.md`, and any data-flow
  description in `docs/PRD.md` and `docs/MASTER-DOCUMENT.md`) MUST be updated to describe
  the new flow with no lingering references to Orchestrator-owned writes.
- **FR-013**: Project governance MUST be reconciled: Constitution Principle II MUST be
  amended or an explicit scoped exception recorded before implementation proceeds, since
  the current principle forbids agent-owned database writes.
- **FR-014**: The kickoff architecture presentation
  (`docs/presentation/ARCHITECTURE-DECK.html`) MUST be updated so its architecture
  diagram and narrative match the new flow.

### Constitution-Aligned Requirements *(mandatory)*

- **CAR-001**: This feature affects the core demo path. It touches live rehearsal capture
  (video + audio persistence), PPTX upload persistence, session end, and
  `/session/:id/report` assembly. Equivalent end-to-end output is required (FR-011).
- **CAR-002**: Changed contracts: the database becomes the shared read/write contract
  between agents and the Orchestrator (agreed location/schema per data kind, FR-006); a
  new agent→Orchestrator **completion-signal** contract is introduced (FR-004);
  Orchestrator entry points that previously accepted raw payloads for persistence change
  role. Whether existing typed WebSocket/shared-types payloads change for the live
  feedback stream MUST be confirmed during planning; the live feedback contract SHOULD
  remain stable.
- **CAR-003**: Session isolation MUST be preserved. Every input-ingress path and any
  completion/notification channel MUST continue to enforce the correct `session_id` and
  `access_token`; report read access continues to honor the opt-in `share_token`. Agents
  writing directly MUST write only within their authenticated session scope.
- **CAR-004**: Fallback/retry/timeout/replay behavior MUST be preserved (FR-010): bounded
  external-call latency, audio-only fallback on repeated Vision timeouts with score
  reweighting, a bounded Orchestrator wait/timeout when a completion signal is missing or
  data is not yet durable, and full `DEMO_MODE=replay` compatibility.
- **CAR-005**: No user-facing UI changes are expected. If the report or status UI changes,
  non-color status/score indicators MUST be preserved. (Likely not applicable.)

### Key Entities *(include if feature involves data)*

- **Session**: The rehearsal record and its lifecycle state (ACTIVE → ENDED →
  REPORT_READY); also carries readiness flags such as `pptx_ready`. Owner of state
  transitions: Orchestrator, driven by completion signals.
- **Video Event**: A noteworthy posture/gesture/face observation produced by the Vision
  agent; now written by the Vision agent. Batched.
- **Transcript Entry**: A speech segment produced by the Audio agent; now written by the
  Audio agent.
- **Audio Warning**: A filler-word / pacing warning produced by the Audio agent; now
  written by the Audio agent.
- **Slide Analysis + Raw Slide Text**: Deck findings and extracted text produced by the
  PPTX agent; now written by the PPTX agent.
- **Content Analysis / Report**: Post-session aggregates. The Report output is the final
  artifact the Orchestrator assembles by reading the agreed location.
- **Completion Signal**: A new notification emitted by an agent identifying the session
  and the kind of work finished; consumed by the Orchestrator to know when to read and
  when to transition session state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of agent-produced results (video events, transcript entries, audio
  warnings, slide analyses, raw slide text) are written by their owning agent; 0% are
  written by the Orchestrator after the change.
- **SC-002**: Every agent emits a completion signal for each unit of work it finishes;
  the Orchestrator's report assembly reads exclusively from the agreed database location.
- **SC-003**: A full demo run (upload → rehearse → end → report) produces a report whose
  scores and insights match the pre-change baseline within the existing dedup/scoring
  tolerance (no user-visible regression).
- **SC-004**: Live feedback continues to reach subscribers during a rehearsal with no
  user-visible latency increase beyond the existing batching window.
- **SC-005**: With `DEMO_MODE=replay`, the entire flow completes successfully end-to-end.
- **SC-006**: Audio-only fallback still activates after repeated Vision timeouts and the
  report reweights scores accordingly.
- **SC-007**: `docs/TECH-ARCHITECTURE-C4.md` and `docs/presentation/ARCHITECTURE-DECK.html`
  contain zero statements describing the Orchestrator as sole DB writer or as the raw-input
  relay; all data-flow descriptions match the implemented model.

## Assumptions

- The system remains a single-process async FastAPI application; "notify" means an
  in-process signal/event, not a new external queue or message broker (Principle V).
- The "agreed place" is the existing PostgreSQL database and its tables; no new storage
  layer is introduced.
- The live feedback WebSocket broadcast remains the mechanism for real-time subscriber
  updates; only the persistence ownership moves to agents.
- Input ingress endpoints (video/audio WebSockets, PPTX upload route) keep their current
  authentication and remain the entry points; "direct to agent" means the agent — not the
  Orchestrator — owns processing and persistence for that input.
- Post-session agents (Content, Report) already read from the database; their read-side
  behavior is largely unchanged, with the Report agent now reading agent-written data.
- Constitution amendment for Principle II will be handled as part of this feature's
  governance step (FR-013) before implementation begins.

## Dependencies

- **Constitution amendment / exception** for Principle II "Contracted Agent Boundaries"
  (FR-013) is a hard prerequisite to implementation, because the principle currently
  forbids agent-owned database writes.
- Existing database schema and repository layer (the shared read/write contract).
- Existing live feedback broadcaster and session-auth middleware (must remain intact).
- `DEMO_MODE=replay` fixtures (must remain compatible).

## Out of Scope

- Introducing any new external infrastructure (message broker, queue, cache, separate
  services) — explicitly excluded by Principle V unless a concrete constraint forces it.
- Changing the report scoring model, rubric, or user-facing report UI.
- Changing the capture frame rates, STT provider, or vision provider behavior.
- User accounts or any change to the capability-token security model.

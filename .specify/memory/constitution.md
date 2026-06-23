<!--
Sync Impact Report
Version change: template -> 1.0.0
Modified principles:
- Template Principle 1 -> I. Demo-First Vertical Slices
- Template Principle 2 -> II. Contracted Agent Boundaries
- Template Principle 3 -> III. Session Isolation and Explicit Sharing
- Template Principle 4 -> IV. Resilience Before Polish
- Template Principle 5 -> V. Native Stack, Minimal Abstractions
Added sections:
- Technical Constraints
- Development Workflow and Quality Gates
Removed sections:
- None
Templates requiring updates:
- ✅ .specify/templates/plan-template.md
- ✅ .specify/templates/spec-template.md
- ✅ .specify/templates/tasks-template.md
- ✅ .specify/templates/checklist-template.md
- ✅ .specify/templates/agent-file-template.md
- ✅ .specify/templates/commands/*.md (directory absent; no command templates to update)
Runtime guidance requiring updates:
- ✅ README.md (already aligned; no edit required)
- ✅ docs/PRD.md (already aligned; no edit required)
- ✅ docs/TECH-ARCHITECTURE-C4.md (already aligned; no edit required)
Follow-up TODOs:
- None
-->

# OctoPrep2000 Constitution

## Core Principles

### I. Demo-First Vertical Slices

Every feature MUST preserve the end-to-end demo path: upload PPTX, start a rehearsal,
capture session data, end the session, and render `/session/:id/report`. Work MUST be
planned in independently demonstrable slices, with Phase 1 functionality protected
before Phase 2 or Phase 3 additions. Stretch work MUST NOT block, destabilize, or
redefine the core report flow.

Rationale: the project exists for a one-day Fuse Day demo. A partial but working slice
beats a broader feature set that cannot be shown live.

### II. Contracted Agent Boundaries

Agents MUST communicate through typed payload contracts and the Orchestrator. The
Orchestrator MUST own all writes to PostgreSQL after validating payloads. Agents MAY
read narrowly scoped context when their role requires it, but they MUST NOT bypass the
Orchestrator for writes or couple directly to unrelated agents. Shared WebSocket payload
types MUST remain explicit and versionable.

Rationale: single-process async architecture only stays debuggable if ownership and
data flow are strict. Direct agent-to-agent or agent-to-database writes create hidden
race conditions and make report generation unreliable.

### III. Session Isolation and Explicit Sharing

All session-scoped operations MUST require the correct `session_id` and `access_token`,
except `POST /sessions` and read-only report access through an opt-in `share_token`.
Reports MUST be private by default. Tokens MUST NOT be committed, logged intentionally,
or embedded in persistent documentation. WebSocket authentication MUST happen before a
client can publish to or subscribe from a session stream.

Rationale: the MVP has no user accounts, so capability tokens are the security boundary.
Weakening them lets one presenter affect or inspect another presenter's session.

### IV. Resilience Before Polish

Every live-session path MUST degrade safely. `/health`, WebSocket reconnect, rate
limiting, batched high-volume writes, `DEMO_MODE=replay`, and audio-only fallback MUST
be preserved when changing the capture, agent, or report pipelines. External AI or STT
calls MUST have bounded latency, clear failure handling, and a demo-safe fallback path.

Rationale: external provider latency, quota, and network failures are likely demo-day
risks. The product is only credible if failures are contained and the rehearsal can
continue.

### V. Native Stack, Minimal Abstractions

Solutions MUST use the selected stack unless a concrete constraint proves otherwise:
TanStack Start with React and TypeScript, FastAPI with Python 3.11+, SQLAlchemy async,
PostgreSQL 15, pnpm workspaces, and uv. New packages, services, queues, storage layers,
or framework abstractions require an explicit plan justification and a rejected simpler
alternative. Prefer native browser, Python, and platform capabilities over dependencies
where practical.

Rationale: the time budget is too small for speculative infrastructure. The existing
single-process architecture is intentionally simple and optimized for parallel team
execution.

## Technical Constraints

- The backend MUST remain a single FastAPI process for the hackathon scope; all agents
  run as async tasks unless the constitution is amended.
- PostgreSQL MUST be the system of record for sessions, transcript entries, video
  events, slide analyses, and reports.
- PPTX analysis MUST use the Tikal Presentation Skills Playbook as its rubric and MUST
  produce slide-specific findings.
- The report MUST deduplicate recurring issues into consolidated insights with
  timestamps, slide numbers, or transcript quotes.
- Live feedback UI is optional stretch work and MUST remain user-toggleable. Default
  behavior MUST keep the final report as the primary feedback surface.
- Vision processing MUST cap effective output to the Vision agent at no more than 5 fps;
  60 fps analysis is prohibited.
- Report generation SHOULD complete within 60 seconds of session end; plans that risk
  missing this target MUST document mitigation.
- Accessibility requirements from the PRD apply to user-facing UI: color MUST NOT be the
  sole indicator of meaning.

## Development Workflow and Quality Gates

- Specifications MUST define prioritized, independently testable user stories and MUST
  identify whether each story affects the core demo path.
- Plans MUST include a Constitution Check before research/design and repeat it after
  design. Any violation MUST include a simpler alternative and why it was rejected.
- Tasks MUST preserve user-story grouping and include validation for backend contracts,
  WebSocket/auth behavior, fallback behavior, and the report UI when affected.
- Backend changes to routes, payloads, data models, scoring, or agent orchestration MUST
  include automated tests unless explicitly documented as a time-boxed demo exception.
- Frontend changes to the session or report flow MUST include a manual verification path
  covering desktop and mobile layouts.
- Demo-day hardening features MUST be validated before declaring a feature complete when
  the feature touches live capture, external providers, or report generation.
- Documentation updates MUST accompany changes that alter endpoint contracts, scoring
  weights, environment variables, or team workflow.

## Governance

This constitution supersedes conflicting ad hoc practices in specs, plans, tasks, and
runtime guidance. Amendments MUST be made by editing this file, documenting the impact in
the Sync Impact Report, and propagating any required changes to dependent templates and
runtime docs.

Versioning follows semantic versioning:
- MAJOR: removes or redefines a core principle or governance rule in a backward
  incompatible way.
- MINOR: adds a principle, adds a governed section, or materially expands compliance
  obligations.
- PATCH: clarifies wording, fixes mistakes, or makes non-semantic refinements.

Every feature plan MUST pass the Constitution Check before implementation. Reviewers
MUST treat unaddressed constitution violations as blockers unless the plan records an
explicit, time-boxed exception with owner and follow-up. Exceptions expire after the
hackathon demo and MUST NOT become default practice without a constitution amendment.

**Version**: 1.0.0 | **Ratified**: 2026-06-23 | **Last Amended**: 2026-06-23

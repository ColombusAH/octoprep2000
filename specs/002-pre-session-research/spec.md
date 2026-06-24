# Feature Specification: Pre-Session Topic Research Persistence

**Feature Branch**: `002-pre-session-research`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "currently the content agent is getting relevant data about the subjects of the session etc, we want to make it in the pptx workflow since it is before the session and to keep so the content analyser can use it without need to call context7 etc to get that also"

## Summary

Topic research (official documentation and articles/improvement guidance about the session subject) is currently fetched **after** the rehearsal, inline with content analysis, and then discarded. This feature moves that research into the **pre-session** preparation flow that already runs after a deck is uploaded, and **persists** the fetched reference material with the session. At session end, the content analyser reads the saved research instead of fetching it live, so report generation no longer waits on external research providers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Persisted Research Reused at Report Time (Priority: P1)

As a presenter who has uploaded a deck for a technical talk, I want the system to gather background reference material about my topic before I rehearse, so that when my report is generated it reflects authoritative sources **and** is produced faster, without re-querying external research services at the end.

**Why this priority**: This is the core of the change — research becomes a pre-session asset rather than a post-session cost. It removes external-provider latency and failure risk from the report-generation path, which is the most time-sensitive moment.

**Independent Test**: Upload a deck with a technical topic, let pre-session preparation complete (which now gates session start), then run a rehearsal and end the session. Verify the report's technical content findings reflect retrieved reference material, and verify that no external research provider is contacted during report generation (research was already saved).

**Acceptance Scenarios**:

1. **Given** a session with a technical topic and an uploaded deck, **When** pre-session preparation completes, **Then** reference material for the topic is saved with the session and a research status is recorded.
2. **Given** a session whose pre-session preparation (including research) has not yet finished, **When** the presenter views the session, **Then** starting the rehearsal is not enabled until preparation completes.
3. **Given** a session whose pre-session research was saved, **When** the session ends and the report is generated, **Then** the content analyser uses the saved reference material and performs no live research-provider calls.
4. **Given** a session with saved research, **When** the report is generated, **Then** the technical content findings and `research_status` are equivalent in quality to the previous inline-research behaviour.

---

### User Story 2 - Safe Degradation When Pre-Session Research Fails (Priority: P1)

As a demo operator or presenter, I want deck preparation and the rehearsal-to-report flow to keep working even when research providers are unavailable, slow, or misconfigured, so a research problem never blocks deck readiness or report generation.

**Why this priority**: Constitution principle IV (Resilience Before Polity) and the hackathon demo path require external-provider failures to be contained. Moving research earlier must not introduce a new way to block the deck-ready signal or the report.

**Independent Test**: Disable or misconfigure the research providers, upload a deck, and complete a rehearsal. Verify the deck still becomes ready, the report is still generated, and the report clearly indicates research was unavailable.

**Acceptance Scenarios**:

1. **Given** research providers are unreachable during pre-session preparation, **When** preparation runs, **Then** the research step resolves within its timeout, the deck still becomes ready, session start unlocks, and the saved research status is `skipped`.
2. **Given** only some providers succeed during pre-session preparation, **When** preparation completes, **Then** the partial reference material is saved and the status is `partial`.
3. **Given** demo replay mode is active, **When** pre-session preparation runs, **Then** no live research is attempted and the saved status reflects replay/not-applicable behaviour.
4. **Given** saved research is missing or unreadable at report time (e.g. pre-session research never ran), **When** the report is generated, **Then** content analysis still completes using transcript-only reasoning and surfaces an appropriate research status.

---

### User Story 3 - Non-Technical and Empty Topics Skip Research (Priority: P2)

As a presenter giving a non-technical talk, I want the system to recognise that external technical research does not apply, so no unnecessary lookups run and the report does not imply missing technical grounding.

**Why this priority**: Preserves existing classifier behaviour and avoids noise/cost for talks where documentation lookups add no value.

**Independent Test**: Upload a deck for a non-technical topic, complete preparation, and generate the report. Verify research status is `not_applicable` and no reference material was fetched.

**Acceptance Scenarios**:

1. **Given** a session whose topic is classified non-technical, **When** pre-session preparation runs, **Then** research is not attempted and the saved status is `not_applicable`.
2. **Given** a session with an empty or missing topic, **When** preparation runs, **Then** research is skipped without error.

---

### Edge Cases

- What happens when a deck is re-uploaded for the same session? Saved research is refreshed/replaced for that session rather than duplicated.
- What happens when the topic is edited after pre-session research already ran? The report uses whatever research was saved; staleness is acceptable for the MVP and noted as an assumption.
- What happens when a session has no uploaded deck but still reaches report generation? Content analysis proceeds without saved research (transcript-only), status reflects that research was not available.
- What happens when saved reference material exceeds the size budget? It is capped/truncated at persistence time so report-time prompts stay within limits.
- What happens before pre-session research finishes? Starting the rehearsal is gated on the pre-session preparation flow completing, so the research step always resolves (success, partial, or contained failure within its timeout) before the session can start. There is no rehearsal-vs-research race at report time.
- What happens when a research provider hangs? The research step is bounded by its timeout so pre-session preparation still finishes and unlocks session start; the outcome is recorded as `partial` or `skipped`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST perform topic research (official documentation and article/improvement guidance about the session subject) during the pre-session deck-preparation flow rather than during post-session content analysis.
- **FR-002**: The system MUST persist the fetched reference material with the session so it survives until report generation and a process restart between rehearsal and report.
- **FR-003**: The system MUST persist a research status for the session with values `full`, `partial`, `skipped`, or `not_applicable`, determined when pre-session research runs.
- **FR-004**: At report time, the content analyser MUST read the persisted reference material and MUST NOT make live calls to external research providers.
- **FR-005**: The system MUST classify the topic before researching and MUST NOT fetch research for non-technical or empty topics (status `not_applicable`).
- **FR-006**: Starting the rehearsal MUST be gated on the pre-session preparation flow (deck analysis + research) completing, so research is always resolved before a session can start.
- **FR-007**: Pre-session research failure (timeout, provider error, missing credentials) MUST NOT prevent pre-session preparation from completing; the research step MUST resolve within a bounded timeout and the deck MUST still become ready (status `partial` or `skipped`).
- **FR-008**: When persisted research is absent or unreadable at report time (e.g. a session that never ran pre-session preparation), content analysis MUST still complete using transcript-only reasoning and surface a research status consistent with that outcome.
- **FR-009**: Demo replay mode MUST bypass all live research during pre-session preparation, matching existing replay behaviour.
- **FR-010**: Persisted reference material MUST be bounded to a size budget that keeps report-time analysis prompts within their existing limits.
- **FR-011**: Persisted research MUST be scoped to a single session and MUST NOT leak across sessions.
- **FR-012**: Re-running pre-session preparation for a session MUST refresh/replace that session's saved research rather than accumulate duplicates.
- **FR-013**: The report's surfaced research status MUST remain equivalent to today's behaviour from the report consumer's perspective (same status values, same insight-injection rules for `partial`/`skipped`).

### Constitution-Aligned Requirements *(mandatory)*

- **CAR-001**: Affects the core demo path at two points — **PPTX upload / pre-session preparation** (research now runs and persists here, and gates session start) and **`/session/:id/report`** (content analysis now reads persisted research). Live rehearsal capture and the real-time path are unaffected once started.
- **CAR-002**: Changes the persistence contract by adding stored research material + research status to the session's data. The post-session content-analysis payload and report API surface for `research_status` / `content_research_status` remain unchanged in shape and values. No WebSocket or shared-type real-time payload change.
- **CAR-003**: Persisted research is read and written only for the owning session; report retrieval continues to honour `access_token` / `share_token` as today. No new cross-session read path is introduced.
- **CAR-004**: Per-provider timeouts, partial fallback, and missing-credential skipping are preserved and now applied in the pre-session flow. `DEMO_MODE=replay` bypasses research. Report generation degrades to transcript-only when saved research is absent.
- **CAR-005**: No new UI surface. The existing Technical Content research-status indicator (text, not color-only) continues to convey `full`/`partial`/`skipped`/`not_applicable` unchanged.

### Key Entities *(include if feature involves data)*

- **Session Research Record**: The persisted reference material for one session. Holds the topic it was gathered for, a collection of reference snippets (each with source type, title, optional URL, excerpt text, and originating provider), the set of providers attempted and succeeded, and the resulting research status. Scoped one-to-one with a session. Bounded in total size.
- **Research Status**: Categorical outcome (`full` / `partial` / `skipped` / `not_applicable`) describing how completely research was gathered; consumed by the report to drive disclaimer/insight behaviour.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Report generation for a technical session makes **zero** external research-provider calls when pre-session research was saved.
- **SC-002**: For sessions where pre-session research completed, the report's technical content findings and research status are equivalent in quality to the previous inline-research behaviour (no regression in surfaced findings or status values).
- **SC-003**: Report generation no longer includes research-fetch wait time; end-to-end report time for technical sessions is reduced by at least the previous research phase duration (target: ≥10 seconds saved at session end for healthy-provider technical sessions).
- **SC-004**: 100% of pre-session preparations complete the deck-ready signal (and unlock session start) even when all research providers fail, within the bounded research timeout.
- **SC-005**: Saved research never causes report-time prompts to exceed their existing size limits (0 truncation-related failures).
- **SC-006**: Demo replay sessions perform no live research lookups during pre-session preparation.

## Assumptions

- The existing topic classifier and research providers (official-docs lookup and article/improvement search) are reused as-is; only the timing and persistence of their output change.
- Research is gathered once per session at pre-session time; topic edits made after research runs are not re-researched for the MVP (staleness accepted).
- Persisting reference material mirrors the existing pattern of saving extracted deck data with the session (a session-scoped stored blob), avoiding new cross-cutting infrastructure.
- The report-facing research-status values and insight-injection rules from the prior feature remain the contract; this feature changes where/when status is produced, not its meaning.
- Pre-session preparation runs off the real-time rehearsal path as a background step, as the deck-analysis preparation already does, and now includes the research step.
- Session start is gated on pre-session preparation completing (deck readiness already signals this); adding research into that flow means research is always resolved before rehearsal begins, so there is no rehearsal-vs-research race.

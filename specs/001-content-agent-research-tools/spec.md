# Feature Specification: Content Agent Research Tools

**Feature Branch**: `001-content-agent-research-tools`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "Improve the content agent by adding tools that improve analysis. For technical topics, search for articles (e.g. Exa/OpenSearch) and fetch official documentation (e.g. Context7). Also search for improvement-oriented reference data to enrich feedback."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Grounded Technical Accuracy Check (Priority: P1)

As a presenter rehearsing a technical talk (e.g. "React 19 new features"), I want my content score and findings to reflect current authoritative sources—not only static model knowledge—so that factual errors and missing sub-topics are caught against what experts and official docs actually say today.

**Why this priority**: This is the core value of the enhancement. Without external grounding, the content agent cannot reliably evaluate fast-moving technical subjects or distinguish outdated claims from current facts.

**Independent Test**: End a session with a technical topic and a transcript containing at least one verifiable claim and one obvious omission. Verify the report's Technical Content panel includes findings that reference externally retrieved knowledge (e.g. a coverage gap for a headline feature documented in official sources, or a factual correction aligned with retrieved documentation).

**Acceptance Scenarios**:

1. **Given** a session with topic "Kubernetes networking basics" and a transcript discussing pods but omitting services, **When** the session ends and the report is generated, **Then** the content findings include at least one coverage-gap insight tied to an expected sub-topic supported by retrieved reference material.
2. **Given** a session with a technical topic and a transcript containing an outdated factual claim, **When** the report is generated, **Then** the content findings include a factual-error insight with a transcript quote and a correction consistent with retrieved authoritative sources.
3. **Given** a session with a technical topic and accurate, well-covered content, **When** the report is generated, **Then** the content findings include at least one strength highlighting technically sound explanations.

---

### User Story 2 - Improvement-Oriented Research Enrichment (Priority: P2)

As a presenter, I want improvement suggestions in the Technical Content panel to reflect best practices, common pitfalls, and what strong talks on my topic typically cover—so I know not only what I got wrong but how to make the talk better next time.

**Why this priority**: Searching only for fact-checking misses half the coaching value. Improvement-oriented research turns the agent from a validator into a mentor for technical content.

**Independent Test**: Run a session on a technical topic with partial but not terrible coverage. Verify improvement findings suggest concrete enhancements (e.g. recommended sub-topics to add, common audience expectations, pitfalls to avoid) that go beyond generic LLM advice and align with retrieved improvement reference data.

**Acceptance Scenarios**:

1. **Given** a technical session where the presenter covers core concepts but skips widely recommended depth (e.g. trade-offs, migration path, or security implications), **When** the report is generated, **Then** at least one improvement insight recommends a specific enhancement grounded in retrieved best-practice or expert guidance.
2. **Given** a technical session with a common beginner mistake present in the transcript, **When** the report is generated, **Then** an improvement insight calls out the pitfall and suggests a clearer framing or correction approach.
3. **Given** improvement reference data is successfully retrieved, **When** findings are produced, **Then** improvement messages remain specific to the stated topic and transcript—not generic presentation platitudes.

---

### User Story 3 - Safe Degradation and Demo Continuity (Priority: P1)

As a demo operator or presenter, I want content analysis to complete even when external research tools are unavailable, misconfigured, or slow—so report generation never blocks the core rehearsal-to-report flow.

**Why this priority**: Constitution principle IV (Resilience Before Polish) and the hackathon demo path require that external provider failures are contained. This story is co-P1 because a broken report path is worse than a less-grounded score.

**Independent Test**: Run session end with external research disabled or simulated failure. Verify a report still generates within the time budget, demo replay mode is unchanged, and users see an appropriate fallback message rather than a failed report.

**Acceptance Scenarios**:

1. **Given** demo replay mode is enabled, **When** a session ends, **Then** content analysis uses canned fixtures and makes no external research calls.
2. **Given** external research tools are unavailable or time out, **When** a technical session ends, **Then** the report still generates with a content score and findings produced from transcript + topic analysis alone, and the user is informed that live reference lookup was skipped.
3. **Given** a non-technical topic (e.g. "My career journey in sales"), **When** the session ends, **Then** content analysis follows the existing lightweight path without external research calls.

---

### Edge Cases

- What happens when the topic is borderline technical (e.g. "AI trends for business leaders")? The system classifies it as technical when domain-specific factual accuracy and sub-topic coverage are meaningfully evaluable; otherwise it uses the non-technical path.
- What happens when external search returns no useful results? Analysis proceeds with transcript-only evaluation and notes limited reference availability in findings or metadata visible to the user.
- What happens when the transcript is empty? Existing behavior is preserved: content score 0, no findings, no external research calls.
- What happens when research tools exceed the time budget? Partial results are used if available; otherwise the agent falls back to transcript-only analysis without blocking report generation.
- What happens when API keys for research tools are missing? Technical sessions degrade to transcript-only analysis with a clear user-facing indication that enhanced grounding was unavailable.
- What happens when retrieved sources conflict? The agent favors official documentation over general articles for factual disputes and surfaces uncertainty when sources disagree materially.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The content analysis process MUST determine whether a session topic is technical before invoking external research.
- **FR-002**: For technical topics, the system MUST retrieve relevant reference material from two categories before final scoring: (a) authoritative documentation for the subject domain, and (b) recent articles or expert write-ups on the topic.
- **FR-003**: For technical topics, the system MUST retrieve improvement-oriented reference data—including recommended sub-topics, common pitfalls, and best-practice guidance—for use when generating improvement insights.
- **FR-004**: Content findings (factual errors, coverage gaps, strengths) MUST be produced using the transcript, session topic, optional slide text, and any successfully retrieved reference material.
- **FR-005**: Each factual-error and coverage-gap finding MUST continue to include a verbatim `context_quote` from the transcript when applicable.
- **FR-006**: Improvement insights MUST be specific, actionable, and tied to the stated topic and transcript—not generic coaching filler.
- **FR-007**: The system MUST produce a `content_score` (0–100) reflecting accuracy and coverage relative to retrieved reference material when available, and relative to transcript analysis alone when reference retrieval is skipped or partial.
- **FR-008**: Content analysis MUST complete as part of report generation without exceeding the existing post-session time budget (60 seconds end-to-end for the full report path).
- **FR-009**: External research MUST be bounded by configurable timeouts and retry limits so a single slow provider cannot block report delivery.
- **FR-010**: Demo replay mode MUST bypass all external research and return fixture-based content analysis unchanged.
- **FR-011**: Non-technical topics MUST use the existing transcript-only analysis path with no external research calls.
- **FR-012**: When external research is skipped or fails, the user MUST see an indication in the Technical Content panel that enhanced reference lookup was not used for that session.
- **FR-013**: The existing content analysis output contract consumed by report generation MUST remain compatible so voice, body, slide scoring and overall report weights are unaffected unless explicitly changed in a separate feature.

### Constitution-Aligned Requirements *(mandatory)*

- **CAR-001**: **Core demo path impact**: Yes—this feature affects session end and `/session/:id/report` content scoring. It MUST NOT break PPTX upload, live rehearsal capture, or report rendering. Phase 1 demo path remains intact with replay mode as the safe fallback.
- **CAR-002**: **Contract changes**: The outward `ContentAnalysisPayload` shape SHOULD remain stable for report aggregation. New fields (e.g. `research_status`, `sources_consulted`) MAY be added only if backward-compatible with report generation and shared types. Any new environment configuration for research providers MUST be documented.
- **CAR-003**: **Session isolation**: Content analysis continues to run per `session_id` with data read only for that session's transcript, topic, and slide analyses. No cross-session data leakage. Report access rules (`access_token`, `share_token`) are unchanged.
- **CAR-004**: **Resilience**: External research MUST have timeouts, bounded retries, and graceful fallback to transcript-only analysis. Demo replay MUST remain functional. Report generation MUST NOT fail solely because research tools failed.
- **CAR-005**: **Accessibility**: If the Technical Content panel disclaimer or status messaging changes, status MUST NOT rely on color alone (e.g. include text such as "Reference lookup unavailable" alongside any visual indicator).

### Key Entities *(include if feature involves data)*

- **Session Topic**: The user-provided subject string and optional context used to scope research queries and evaluation.
- **Transcript**: Ordered speech text assembled post-session; primary evidence for quotes and claim detection.
- **Reference Bundle**: Ephemeral collection of retrieved documentation excerpts, articles, and improvement guidance used during a single analysis run—not persisted as a first-class user artifact in MVP unless needed for debugging.
- **Content Finding**: A scored insight (`FACTUAL_ERROR`, `COVERAGE_GAP`, `STRENGTH`) with message and optional transcript quote; may implicitly reflect retrieved sources in its message.
- **Research Status**: Per-session indicator of whether full, partial, or no external research was used—surfaced to the user in the report.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For technical test sessions with known omissions, at least 80% of generated coverage-gap findings align with sub-topics present in retrieved authoritative reference material (validated by human review of a fixed test set of ≥5 scenarios).
- **SC-002**: For technical test sessions with deliberate factual errors, at least 80% of factual-error findings match corrections supported by retrieved documentation or high-quality articles (validated on the same fixed test set).
- **SC-003**: At least 70% of improvement insights in technical sessions reference topic-specific enhancements (recommended sub-topics, pitfalls, or best practices) rather than generic advice (validated by human review).
- **SC-004**: 100% of session-end report generations complete within 60 seconds in demo replay mode and in degraded mode when research tools are unavailable.
- **SC-005**: 95% of session-end report generations complete within 60 seconds when research tools are healthy (measured over a representative batch of technical sessions).
- **SC-006**: Presenters viewing the Technical Content panel can distinguish sessions analyzed with full reference lookup vs. fallback analysis via explicit on-screen status text.

## Assumptions

- "Technical topic" is auto-classified from the session topic (and optional topic context) using a lightweight determination step; presenters are not asked to manually toggle research mode.
- Official documentation retrieval is scoped to libraries and products identifiable from the topic (e.g. "React 19", "Kubernetes", "PostgreSQL").
- Article search supplements documentation with recent expert perspectives, release notes commentary, and practitioner guides—not as a replacement for official docs on factual disputes.
- Improvement-oriented research queries target patterns such as "best practices", "common mistakes", "what to cover", and "audience expectations" for the stated topic.
- External tool providers (e.g. Exa for article search, Context7 for documentation) are available via API keys configured in the deployment environment; the specification does not mandate a specific vendor beyond the user-stated preference.
- OpenSearch is treated as an optional article-index backend; if not configured, article search uses the configured search provider (e.g. Exa) without blocking delivery.
- Retrieved reference material is used ephemerally during analysis and is not required to be stored long-term in the database for MVP.
- The existing UI disclaimer about model training cutoff will be updated to reflect that technical sessions may also use live reference lookup when available.
- Slide text from prior PPTX analysis may continue to enrich context but is not a substitute for transcript-based findings.
- Non-technical topics (personal narratives, soft-skills talks without verifiable domain claims) do not benefit enough from external research to justify latency and cost.

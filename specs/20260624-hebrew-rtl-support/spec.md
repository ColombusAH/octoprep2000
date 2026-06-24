# Feature Specification: Hebrew & RTL Support

**Feature Branch**: `20260624-hebrew-rtl-support`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "we nned to support hebrew, and the ui also should support rtl." Clarified: the uploaded presentation can be in English while the presenter speaks Hebrew during rehearsal; the user must be able to choose whether to view the report in Hebrew or English, independent of the language spoken during rehearsal. Revised: the presenter explicitly chooses, before starting a rehearsal, which language they will speak and which language the uploaded deck is in (no automatic detection of either); the user separately and explicitly decides whether to view the report in Hebrew or English.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declare speech and deck language, then rehearse in Hebrew (Priority: P1)

Before starting a rehearsal, a presenter explicitly selects which language they will speak (Hebrew or English) and which language their uploaded deck is in (Hebrew or English) — independently of each other. The system then captures and transcribes the rehearsal accurately in the declared spoken language and keeps it correctly aligned to slides and timestamps, regardless of whether the deck language matches the spoken language.

**Why this priority**: This is the foundational capability. Without an accurate, intentional record of which language was spoken and which language the deck is in, there is no reliable transcript, voice-coaching signal, or report content to translate, toggle, or display — every other story depends on this working first.

**Independent Test**: Start a new session, select "Hebrew" as the speech language and "English" as the deck language, upload an English PPTX, speak entirely in Hebrew, end the session, and verify the stored transcript contains accurate Hebrew text correctly mapped to slide numbers and timestamps.

**Acceptance Scenarios**:

1. **Given** a presenter is starting a new session, **When** they reach the session-setup step, **Then** they can explicitly select their speech language (Hebrew or English) and their deck's language (Hebrew or English) as two independent choices, before the rehearsal begins.
2. **Given** a presenter selected Hebrew as their speech language and uploaded an English-language deck, **When** they start the live rehearsal and speak in Hebrew, **Then** the system transcribes the spoken Hebrew accurately and associates each transcript segment with the correct slide and timestamp.
3. **Given** a rehearsal session in progress, **When** the presenter momentarily reads an English slide title or term aloud while otherwise speaking Hebrew, **Then** the transcript captures both languages without breaking the session timeline or losing segments.

---

### User Story 2 - Choose report language independent of spoken language (Priority: P1)

After a session ends, the user opens the report and can choose to view it in Hebrew or English. The report's scores, narrative feedback, slide-specific findings, and transcript quotes display correctly in whichever language is selected, regardless of the language the presenter actually spoke.

**Why this priority**: This is the second explicitly requested capability and the primary point of value for a Hebrew-speaking presenter — being able to read their own feedback in their preferred language.

**Independent Test**: Open the report for a session where the presenter spoke Hebrew, toggle the report language to English and verify all report content renders in English, then toggle back to Hebrew and verify it renders in Hebrew with right-to-left layout.

**Acceptance Scenarios**:

1. **Given** a completed session report for a Hebrew-spoken rehearsal, **When** the user selects "English" as the report language, **Then** all narrative feedback, slide-specific findings, and transcript quotes display in English.
2. **Given** a completed session report, **When** the user selects "Hebrew" as the report language, **Then** the report content displays in Hebrew and the report layout mirrors to right-to-left.
3. **Given** a user has not yet made an explicit language choice, **When** they open a report, **Then** the system defaults the display language to the language the presenter actually spoke during the rehearsal.

---

### User Story 3 - Use the dashboard UI in Hebrew with RTL layout (Priority: P3)

A user sets their interface language preference to Hebrew and navigates the rest of the dashboard (start/upload, settings, archive, leaderboard). Static UI text appears in Hebrew and the layout mirrors to right-to-left, while functionality remains identical to the English/LTR experience.

**Why this priority**: This extends Hebrew/RTL support to the rest of the product for a consistent experience, but the core demo value is already delivered by Stories 1 and 2 even if secondary screens remain English-only at first.

**Independent Test**: Switch the interface language setting to Hebrew, navigate through the main dashboard screens, and verify labels, buttons, and static text appear in Hebrew with correctly mirrored RTL layout, with no loss of functionality.

**Acceptance Scenarios**:

1. **Given** a user sets their interface language to Hebrew in Settings, **When** they navigate the dashboard, **Then** navigation labels, buttons, and static text appear in Hebrew with RTL layout.
2. **Given** the interface language is set to English, **When** the user uses the app, **Then** layout and behavior are unchanged from current behavior.

---

### Edge Cases

- What happens when the presenter code-switches between Hebrew and English within the same sentence, even though they declared a single speech language up front?
- How does the live capture UI handle mixed-direction text when slide content is shown in English while the live transcript is in Hebrew?
- What happens when Hebrew transcription confidence is low (background noise, accent, unclear audio) — is an uncertain quote flagged in the report rather than silently shown as fact?
- What happens if a presenter declares a deck or speech language that doesn't match reality (e.g., selects "English" deck language but the uploaded deck is actually in Hebrew)? Does the system trust the declared language as-is, or surface a mismatch warning?
- Does a user's manual report-language override persist if they leave and revisit the report later, or does it reset to the spoken-language default each time?
- When a report is shared via a read-only `share_token`, does the viewer see the owner's last-selected language or the spoken-language default?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accurately transcribe Hebrew spoken audio during live rehearsal capture, independent of the uploaded deck's language.
- **FR-002**: System MUST preserve correct timestamp and slide alignment for transcript segments regardless of the language spoken.
- **FR-003**: Users MUST be able to select Hebrew or English as a session report's display language after the session ends.
- **FR-004**: System MUST render report content (scores, narrative coaching feedback, slide-specific findings, transcript quotes) in the user-selected report language, regardless of the language spoken during rehearsal.
- **FR-005**: System MUST mirror UI layout to right-to-left whenever Hebrew is the active display language, including navigation, text alignment, icons, and direction-sensitive components (charts, timelines, progress indicators).
- **FR-006**: System MUST leave the existing English/left-to-right experience unchanged when English is selected, with no regression.
- **FR-007**: Users MUST be able to switch a report's display language at any time while viewing it, without re-recording or re-processing the session.
- **FR-008**: Users MUST explicitly select which language they will speak (Hebrew or English) before starting a rehearsal; the system MUST NOT rely on automatic detection as the source of truth for spoken language.
- **FR-009**: Users MUST explicitly select which language their uploaded slide deck is in (Hebrew or English), independently of their speech-language selection. The system MUST evaluate slide content in the declared deck language rather than assuming it is always English.
- **FR-010**: System MUST default a session report's display language to the presenter's declared speech language (Hebrew speech → Hebrew report by default; English speech → English report by default). The user MUST always be able to explicitly decide and switch to the other language via the toggle (FR-003, FR-007) — the default is a starting point, not a restriction. When a transcript or slide-derived quote is shown in a language different from the one in which it was originally spoken or written, the system MUST display it verbatim in its original language with a small language label rather than machine-translating it, to preserve coaching accuracy.
- **FR-011**: System MUST let users set a default interface (UI chrome) language preference (Hebrew or English) that persists across sessions.
- **FR-012**: System MUST keep status/score indicators distinguishable without relying on color alone, in both LTR and RTL layouts.
- **FR-013**: System MUST recognize Hebrew-language filler words and disfluencies (not only English ones) when scoring voice delivery for a Hebrew-spoken rehearsal, so coaching feedback (filler counts, pacing insights) stays accurate instead of defaulting to a false "no fillers detected" result.

### Constitution-Aligned Requirements *(mandatory)*

- **CAR-001**: This feature affects the core demo path — specifically live rehearsal capture (Hebrew speech-to-text) and the `/session/:id/report` view (report-language toggle, RTL rendering). PPTX upload and session-start flows gain a language-related UI touchpoint but their core logic is unaffected.
- **CAR-002**: Changed contracts: session creation must accept the presenter's two explicit language declarations (speech language, deck language); the session/report data must be able to carry or derive content for two display languages; and the speech-to-text integration must support Hebrew as an input language.
- **CAR-003**: Session-isolation behavior is unchanged by this feature. Language preference and report-language selection MUST be scoped to the requesting user's own session/view and MUST NOT leak or alter another presenter's `access_token`- or `share_token`-protected session data.
- **CAR-004**: Hebrew speech-to-text and report-language rendering MUST have bounded latency and a demo-safe fallback (e.g., falling back to an unlabeled/raw transcript, or `DEMO_MODE=replay` fixtures) if Hebrew transcription or language rendering fails or times out.
- **CAR-005**: RTL layout MUST preserve existing accessibility constraints — status and score meaning MUST remain distinguishable without relying on color, in both LTR and RTL orientations.

### Key Entities

- **Session**: gains two explicitly-declared attributes set at session creation — speech language (Hebrew or English) and deck language (Hebrew or English) — independent of each other.
- **Report**: gains a selectable display-language attribute, independent of the session's declared speech language.
- **Interface Language Preference**: a persisted user setting representing the presenter's chosen UI chrome language (Hebrew or English).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Hebrew speech spoken during rehearsal is transcribed with accuracy comparable to the existing English transcription quality.
- **SC-002**: 100% of completed session reports can be viewed in either Hebrew or English via a single toggle, with no missing or broken content in either language.
- **SC-003**: Users can switch a report's display language and see the change applied in under 2 seconds, without reloading or reprocessing the session.
- **SC-004**: When Hebrew is the active display language, all in-scope dashboard screens render with correct RTL mirroring — no overlapping, truncated, or misaligned text or icons.
- **SC-005**: Switching to or from Hebrew produces zero regressions in the existing English/LTR experience.

## Assumptions

- The presenter's spoken language for a given rehearsal is Hebrew or English; no other languages are required for this feature.
- The PPTX deck's declared language and the presenter's declared speech language are independent and need not match.
- The system trusts the presenter's declared speech and deck language selections as-is; it does not verify them against the actual audio or slide text for this feature.
- A user's report-language choice is a presentation/display choice, not a re-analysis — underlying scores and timestamps do not change when language is toggled.
- The dashboard's existing Settings screen is a suitable place to host a UI-language preference control.
- "RTL UI support" applies to the existing web dashboard; no separate mobile app is in scope.
- Pacing (words-per-minute) thresholds remain a single, language-agnostic calibration; per-language pacing norms are a documented limitation, not required for this feature.

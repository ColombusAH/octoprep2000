# Feature Specification: Demo Audio Coaching

**Feature Branch**: `main`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "For this hackathon project, we are in charge of the audio agent: transcription, filler words, talking speed. This project lives for one day and one demo; count on this in risk management."

**Goal**: Provide believable, reliable audio coaching during the hackathon demo by capturing speech, producing transcript evidence, identifying filler words, and flagging talking-speed issues without allowing provider or capture failures to derail the demo.

**Success Criteria**: A presenter can complete a short rehearsal and receive voice feedback with transcript-backed filler and pacing findings, while the team has a credible fallback path if live audio analysis fails.

**Constraints**: Optimize for one-day demo survivability, not long-term analytics precision; prefer small, visible, dependable behavior over comprehensive production hardening.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Capture Speech Feedback (Priority: P1)

As a presenter rehearsing for the demo, I want the system to listen during my practice session and produce transcript-backed voice feedback so that I can see concrete evidence of how I spoke.

**Why this priority**: This is the minimum viable audio-agent value. Without a transcript and voice findings, the audio agent has nothing meaningful to show in the live demo or final report.

**Independent Test**: Start a short practice session, speak a known script that includes at least one filler word and a fast segment, end the session, and verify that the report contains transcript evidence plus voice feedback.

**Acceptance Scenarios**:

1. **Given** a presenter has started a practice session with microphone access granted, **When** they speak for at least 20 seconds, **Then** the system records transcript segments tied to the session timeline.
2. **Given** the presenter says an obvious filler word such as "um" or "uh", **When** voice feedback is generated, **Then** the report includes a filler-word finding with at least one timestamp.
3. **Given** the presenter speaks noticeably faster than a comfortable presentation pace for a sustained short segment, **When** voice feedback is generated, **Then** the report includes a pacing warning with a timestamp.

---

### User Story 2 - Keep the Demo Alive on Audio Failure (Priority: P2)

As a demo team member, I want audio analysis to degrade into a controlled fallback when live transcription fails so that the demo still shows a coherent voice-coaching story.

**Why this priority**: External speech services, browser permissions, and live microphones are common demo failure points. A one-day hackathon product should avoid visible dead ends more than it should maximize real-world accuracy.

**Independent Test**: Run a session with live transcription unavailable or intentionally disabled, complete the session, and verify that the user still sees a plausible transcript-backed voice report or a clear no-audio outcome that does not block the rest of the demo.

**Acceptance Scenarios**:

1. **Given** the live speech provider is unavailable, **When** the presenter completes a session, **Then** the system either uses prepared demo audio events or clearly continues without blocking session completion.
2. **Given** microphone capture fails before or during a session, **When** the presenter continues or ends the session, **Then** the system shows a user-understandable warning and the final report remains reachable.
3. **Given** fallback demo audio events are used, **When** multiple audio chunks arrive, **Then** the report does not show repeated duplicate transcript or warning entries that make the demo look broken.

---

### User Story 3 - Show Live Coaching When Enabled (Priority: P3)

As a presenter, I want optional live warnings for filler words and pacing so that I can adjust during rehearsal without waiting for the final report.

**Why this priority**: Live feedback is useful and visually compelling, but the final demo can still succeed if the report contains the core audio findings.

**Independent Test**: Enable live feedback, say a known filler word, and verify that a non-blocking warning appears during the session while recording continues.

**Acceptance Scenarios**:

1. **Given** live feedback is enabled, **When** an obvious filler word is detected, **Then** the presenter sees a non-blocking warning during the session.
2. **Given** live feedback is disabled, **When** filler words or pacing issues are detected, **Then** the system still records them for the final report without interrupting the presenter.

---

### Edge Cases

- The presenter grants camera access but denies microphone access; the session should still be able to end cleanly and produce non-audio results.
- The speech provider returns no text for silence or noise; the system should avoid creating misleading transcript entries.
- The presenter uses a word that can be a filler or a meaningful word, such as "like"; the system should avoid over-penalizing ambiguous single occurrences.
- The presenter speaks very little; the report should distinguish insufficient audio from poor delivery.
- The fallback path is activated during a live demo; the output should remain coherent and non-duplicative.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST capture presenter speech during an active practice session when microphone access is available.
- **FR-002**: The system MUST produce timestamped transcript segments for captured speech that contains recognizable words.
- **FR-003**: The system MUST associate all transcript segments and voice warnings with the correct practice session.
- **FR-004**: The system MUST detect obvious filler words, at minimum "um" and "uh", and make them available in the final voice report.
- **FR-005**: The system MUST flag talking-speed issues when the presenter sustains a noticeably too-fast or too-slow pace long enough to be useful feedback.
- **FR-006**: The system MUST include timestamps for filler-word and pacing findings so the presenter can connect feedback to moments in the rehearsal.
- **FR-007**: The system MUST avoid blocking session completion when live transcription is slow, unavailable, or returns no usable text.
- **FR-008**: The system MUST provide a controlled demo fallback that can produce a coherent audio-coaching report when live audio analysis cannot be trusted for the demo.
- **FR-009**: The fallback path MUST avoid duplicating the same prepared transcript or warning events in a way that would be visible in the final report.
- **FR-010**: The system MUST show a user-understandable message when microphone capture fails or disconnects during the session.
- **FR-011**: The final report MUST include a voice score or voice outcome that reflects filler-word and pacing findings when sufficient audio was captured.
- **FR-012**: The system SHOULD avoid surfacing repeated live warnings so frequently that they distract from the rehearsal.

### Constitution-Aligned Requirements *(mandatory)*

- **CAR-001**: This feature affects the core demo path: live rehearsal capture, session end, and `/session/:id/report`.
- **CAR-002**: The feature is expected to use the existing session audio stream, transcript entry, voice warning, scoring, and report contracts; any contract changes must be explicitly documented before planning.
- **CAR-003**: Audio capture and feedback MUST remain isolated by session. Only clients authorized for the active session may publish audio or receive live voice warnings.
- **CAR-004**: Live transcription MUST have demo-safe failure behavior: provider errors, silence, or unavailable speech results must not prevent session completion or report access. Prepared replay data may be used as demo insurance when live providers fail.
- **CAR-005**: Any user-facing warning or status related to audio MUST use clear text in addition to color or visual emphasis.

### Key Entities *(include if feature involves data)*

- **Practice Session**: A single rehearsal owned by one presenter, containing captured speech evidence and final report outcomes.
- **Transcript Segment**: A timestamped piece of recognized presenter speech, optionally marked with filler words found in that segment.
- **Voice Warning**: A timestamped coaching event for filler words, speaking too fast, speaking too slowly, or audio capture problems.
- **Voice Report Outcome**: The final report content summarizing transcript-backed filler and pacing feedback, including timestamps and score/outcome.
- **Demo Fallback Audio Event**: Prepared transcript or warning evidence used only to keep the hackathon demo coherent when live analysis fails.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a planned demo script of 30-60 seconds, the final report shows at least one transcript-backed voice insight within 30 seconds after ending the session.
- **SC-002**: When the script includes one obvious filler word, the final report identifies at least one filler-word finding with a timestamp in 90% of dry runs.
- **SC-003**: When the script includes a deliberately fast 10-second segment, the system produces at least one pacing-related finding in 80% of dry runs.
- **SC-004**: If live transcription is unavailable during a dry run, the presenter can still complete the session and reach a coherent report in under 60 seconds.
- **SC-005**: Fallback demo audio output contains no visibly duplicated transcript or warning rows across a single completed session.
- **SC-006**: Microphone permission or disconnection failures produce a clear user-facing message during the session in 100% of tested failure attempts.

## Assumptions

- The target lifetime is one hackathon day and one live demo; long-term data quality, broad language support, and deep speech analytics are out of scope.
- The primary presenter uses a modern desktop browser with microphone permission available.
- English speech is the default demo language.
- A prepared demo script and fallback audio event set are acceptable demo insurance.
- Final report reliability is more important than perfect live-warning latency.
- Ambiguous filler words should be treated conservatively unless they appear repeatedly or in clearly filler-like contexts.

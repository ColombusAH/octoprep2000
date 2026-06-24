# Feature Specification: Audio Noise Reduction Pipeline

**Feature Branch**: `006-audio-noise-reduction`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "when presenting there are noises from the audience or from the environment — propose an algorithm in order to fix it"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean Transcription Despite Audience Noise (Priority: P1)

A presenter rehearses their deck in a noisy room. The recording captures coughs, chair scrapes, and background voices alongside the presenter's speech. After ending the session, the system produces a transcript that accurately reflects only what the presenter said, without noise artifacts distorting word boundaries or inserting phantom words.

**Why this priority**: Transcription accuracy is the foundation of every scored insight in the report. Noisy input directly degrades slide feedback quality and timestamp accuracy — the core demo value proposition.

**Independent Test**: Record a session with intentional background noise (phone audio, clapping). End session and verify the generated report transcript matches only spoken presentation content.

**Acceptance Scenarios**:

1. **Given** a recorded rehearsal with audible audience noise, **When** the session ends and processing begins, **Then** the transcript returned by STT reflects the presenter's speech with no noise-induced word insertions or deletions.
2. **Given** a recording where audience noise briefly exceeds the presenter's voice volume, **When** processing completes, **Then** the system degrades gracefully — partial transcript is better than a failed transcription.
3. **Given** `DEMO_MODE=replay`, **When** processing begins, **Then** the noise reduction step is bypassed entirely and the canned fixture audio is passed directly to STT.

---

### User Story 2 - Browser Captures Clean Audio by Default (Priority: P2)

A presenter starts recording in the browser. Without any configuration, the browser applies hardware-level noise suppression so that the audio stream reaching the backend is already cleaner than raw microphone input.

**Why this priority**: Browser-side suppression is free, zero-latency, and handles the majority of steady-state ambient noise before any bytes are uploaded. It complements backend processing rather than replacing it.

**Independent Test**: Start a rehearsal session with ambient background music playing. Confirm that the uploaded audio file has noticeably reduced background level compared to what the microphone hears raw (verifiable via waveform inspection or listening test).

**Acceptance Scenarios**:

1. **Given** a browser that supports audio constraints, **When** the recording session starts, **Then** the microphone stream has `noiseSuppression`, `echoCancellation`, and `autoGainControl` enabled.
2. **Given** a browser that does not support one of the constraints, **When** the recording session starts, **Then** recording proceeds without that constraint rather than failing entirely.

---

### User Story 3 - Processing Overhead Is Invisible to the Presenter (Priority: P3)

After ending a rehearsal, the presenter sees the report within the existing expected wait time. Noise reduction processing does not meaningfully extend the time between "End Session" and report availability.

**Why this priority**: Report latency is a constitution constraint (60 seconds). The noise reduction step must not push total processing past this threshold.

**Independent Test**: Record a 5-minute rehearsal session. Measure time from session end to report availability. Confirm it stays within the 60-second constitution target.

**Acceptance Scenarios**:

1. **Given** a 5-minute rehearsal recording, **When** session ends and the full pipeline runs, **Then** report is available within 60 seconds of session end (constitution requirement).
2. **Given** noise reduction processing fails for any reason, **When** the failure is detected, **Then** the raw audio is passed directly to STT — report generation continues without noise suppression rather than failing entirely.

---

### Edge Cases

- What happens when the recording is entirely silence (presenter paused, noise only)?
- What happens when the noise floor estimation window (first 0.5s) captures speech instead of silence?
- What happens if the audio file format is unsupported by the noise reduction library?
- What happens if the noise reduction library is unavailable or throws an exception?
- What happens with very short recordings (under 1 second)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The browser recording MUST request the microphone stream with `noiseSuppression: true`, `echoCancellation: true`, and `autoGainControl: true` audio constraints.
- **FR-002**: The browser recording MUST fall back gracefully if any individual constraint is unsupported — recording MUST NOT fail due to constraint rejection.
- **FR-003**: The backend MUST apply spectral noise gating to uploaded audio before passing it to ElevenLabs Scribe STT, using the first 0.5 seconds as the noise profile baseline.
- **FR-004**: Noise reduction MUST use non-stationary mode to handle dynamic audience noise (claps, coughs, chair scrapes) rather than only steady-state hum.
- **FR-005**: If noise reduction processing fails for any reason, the system MUST fall back to passing raw audio directly to STT and MUST log the failure — transcription MUST NOT be blocked.
- **FR-006**: When `DEMO_MODE=replay` is active, noise reduction processing MUST be skipped entirely and canned fixture audio passed directly to STT unchanged.
- **FR-007**: Noise reduction processing MUST complete within 500ms per minute of audio (5-minute recording = max 2.5s overhead).
- **FR-008**: The feature MUST NOT alter any downstream interface: the same audio-to-STT call signature, transcript format, and report generation pipeline remain unchanged.

### Constitution-Aligned Requirements *(mandatory)*

- **CAR-001**: This feature affects the core demo path — it sits between audio capture and STT transcription, which feeds the report at `/session/:id/report`. It MUST be implemented so the core path (upload → transcribe → score → report) continues to function correctly.
- **CAR-002**: No API contracts, WebSocket payload types, shared TypeScript types, scoring weights, or database schema change. The noise reduction is a transparent pre-processing step internal to the existing STT call.
- **CAR-003**: No changes to session isolation. `access_token` and `share_token` handling are unaffected. Noise reduction operates on the audio bytes before any agent boundary is crossed.
- **CAR-004**: FR-005 and FR-006 define the required fallback behavior. `DEMO_MODE=replay` bypass is mandatory. STT call MUST be attempted even if noise reduction throws. Processing timeout MUST be bounded.
- **CAR-005**: No user-facing UI changes. Browser constraint changes are transparent to the presenter. No new status indicators or accessibility requirements introduced.

### Key Entities

- **AudioBlob**: Raw or noise-reduced audio bytes uploaded from the browser after rehearsal. Passed to STT; not stored persistently beyond the existing pipeline.
- **NoiseProfile**: Transient in-memory estimate derived from the first 0.5s of the audio file. Used by the spectral gating step; discarded after processing. Never persisted.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Transcription word error rate on recordings with moderate audience noise is equal to or lower than on raw unprocessed audio from the same session.
- **SC-002**: Noise reduction processing adds no more than 500ms of overhead per minute of recorded audio (5-minute rehearsal = max 2.5s added latency).
- **SC-003**: End-to-end time from session end to report availability remains within 60 seconds for rehearsals up to 10 minutes long (constitution requirement preserved).
- **SC-004**: Zero new report-generation failures attributable to noise reduction — the fallback path keeps the pipeline viable even when noise processing fails.
- **SC-005**: Browser audio capture succeeds in all major browsers (Chrome, Firefox, Safari) regardless of individual constraint support.

## Assumptions

- The existing audio upload route in the FastAPI backend is the correct integration point — noise reduction is applied there before the ElevenLabs STT call, with no new route or queue introduced.
- A Python audio processing library (`noisereduce` or equivalent) will be added as a dependency. This is justified by Principle V (prefer native capabilities) because no native Python stdlib covers spectral noise gating — the library is minimal and purpose-built.
- The first 0.5 seconds of every rehearsal recording can be assumed to contain pre-speech silence suitable for noise profile estimation. If a presenter starts speaking immediately, processing degrades gracefully (reduced effectiveness, not failure).
- Audio format entering the backend is already the format supported by the processing library (WAV or similar). No re-encoding step is assumed necessary.
- Mobile support is out of scope for v1 — browser constraints and backend processing target desktop Chrome/Firefox/Safari only.
- `noisereduce` with `stationary=False` is sufficient for hackathon-day noise conditions. Advanced model-based suppression (e.g. DeepFilterNet) is out of scope.

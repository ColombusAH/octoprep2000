# Feature Specification: Uploaded Video Batch Analysis

**Feature Branch**: `003-video-upload-analysis`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "currently there is realtime analysis, we want also be able to upload a full video, the system will analyse and make the same but for an uploaded and not realtime"

## Summary

Today a presenter rehearses live in the browser while the system analyses video and audio in real time. This feature adds a second way in: the presenter uploads a single pre-recorded rehearsal video, and the system analyses it in batch — extracting frames and the audio track, running the same vision, speech, slide, and content analysis, and producing the **same** scored report at `/session/:id/report`. There is no live feedback during an uploaded analysis (that is a future phase); the report is the deliverable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload a Recorded Rehearsal and Get the Same Report (Priority: P1)

As a presenter who already recorded a rehearsal (e.g. a screen/camera recording or a download), I want to upload that video instead of rehearsing live, so I get the same coaching report without having to perform on the spot.

**Why this priority**: This is the entire feature — a non-live entry point that yields an equivalent report. Without it there is nothing to demonstrate.

**Independent Test**: Create a session, upload a PPTX, then upload a rehearsal video. After processing completes, open `/session/:id/report` and verify it contains the same sections and scores (voice, body, slide, content) and timestamped insights as a live session would.

**Acceptance Scenarios**:

1. **Given** a session with an analysed deck, **When** the presenter uploads a supported rehearsal video and processing completes, **Then** the report shows voice, body, slide, and content scores plus insights, structurally identical to a live-session report.
2. **Given** an uploaded video with spoken content, **When** processing completes, **Then** the report includes a transcript-derived voice analysis (pacing, filler words) covering the spoken material.
3. **Given** an uploaded video showing the presenter on camera, **When** processing completes, **Then** the report includes body/eye-contact/posture insights derived from the video frames.
4. **Given** an uploaded video, **When** an insight references a moment in the talk, **Then** its timestamp corresponds to the position within the uploaded video (its media timeline), not to upload or wall-clock time.

---

### User Story 2 - Track Processing Progress (Priority: P2)

As a presenter who just uploaded a video, I want clear feedback that analysis is underway and when it is done (or failed), so I know when to open my report and am not left staring at a blank screen.

**Why this priority**: Batch analysis of a multi-minute video is not instant. Without visible progress/completion state the feature feels broken even when it works.

**Independent Test**: Upload a video and observe the session surfaces a processing state, then a completed (or failed) state; the report becomes available only once processing finishes.

**Acceptance Scenarios**:

1. **Given** a video upload has been accepted, **When** analysis is running, **Then** the session reports a "processing" state and the report is not yet presented as ready.
2. **Given** analysis finishes successfully, **When** the presenter checks the session, **Then** it reports a "ready" state and the report is viewable.
3. **Given** analysis fails or the video cannot be processed, **When** the presenter checks the session, **Then** it reports a clear failure state with a human-readable reason and does not hang indefinitely.

---

### User Story 3 - Reject Unsupported or Oversized Inputs Early (Priority: P2)

As a presenter, I want the system to tell me immediately if my file is the wrong type or too long, so I do not wait through a long process only to get nothing.

**Why this priority**: Guards the batch pipeline and gives fast, actionable errors; protects the demo from pathological inputs.

**Independent Test**: Attempt to upload a non-video file, an unsupported video format, and an over-length video; verify each is rejected up front with a specific message and no analysis starts.

**Acceptance Scenarios**:

1. **Given** a file that is not a supported video format, **When** the presenter uploads it, **Then** it is rejected immediately with a message naming the accepted formats.
2. **Given** a video longer than the supported maximum duration, **When** the presenter uploads it, **Then** it is rejected with a message stating the limit.
3. **Given** a video over the maximum file size, **When** the presenter uploads it, **Then** it is rejected with a size-limit message.

---

### Edge Cases

- **Video with no audible speech**: voice/transcript analysis yields little or nothing; the report still generates with whatever other modalities produced (graceful, like a quiet live session).
- **Video with no visible person** (slides-only screen recording): body/vision insights are sparse or absent; voice + slide + content analysis still produce a report.
- **Corrupt or undecodable file** that passes the format check but fails mid-decode: treated as a processing failure (US2 scenario 3), not a crash.
- **External AI/STT provider failure during batch**: analysis degrades to a partial report rather than failing entirely (consistent with live resilience).
- **Demo replay mode active**: uploaded-video analysis uses the same canned fixtures as live replay instead of calling live AI/STT.
- **Re-upload of a video for the same session**: the latest upload's analysis replaces prior batch results for that session rather than accumulating duplicates.
- **Both a live rehearsal and an uploaded video for one session**: out of scope — a session is analysed by one path; see Assumptions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST let the owner of a session upload a single pre-recorded rehearsal video for that session as an alternative to a live rehearsal.
- **FR-002**: The system MUST accept the common consumer video formats produced by typical screen/camera recorders and downloads (e.g. MP4/H.264, QuickTime/MOV, WebM) and MUST reject other file types with a clear message.
- **FR-003**: The system MUST reject videos longer than the supported maximum duration of 15 minutes, and reject files over the maximum size, with specific messages, before starting analysis.
- **FR-004**: The system MUST analyse the uploaded video's visual content to produce the same body-language/eye-contact/posture observations the live path produces.
- **FR-005**: The system MUST extract the audio track from the uploaded video and use it for speech-to-text, producing the same transcript and voice observations (pacing, filler words) the live path produces. No separate audio file is uploaded.
- **FR-006**: The system MUST produce the same downstream report artifacts as a live session (transcript, video observations, audio warnings, slide analysis, content analysis) keyed to the session, so the existing report is generated unchanged.
- **FR-007**: Insight timestamps for an uploaded video MUST map to positions within the video's own media timeline (time from the start of the recording).
- **FR-008**: Visual sampling of the uploaded video MUST NOT exceed 5 frames per second of effective analysis (matching the live cap).
- **FR-009**: The system MUST run uploaded-video analysis off the request path (as background work) and MUST surface processing, ready, and failure states for the session.
- **FR-010**: Analysis MUST NOT present the report as ready until batch processing has finished writing all its results.
- **FR-011**: External provider failures or undecodable media MUST degrade safely — a partial report when possible, an explicit failure state otherwise — and MUST NOT crash the session or block other sessions.
- **FR-012**: Demo replay mode MUST bypass live AI/STT for uploaded videos using the same canned fixtures as the live replay path.
- **FR-013**: The uploaded-video path MUST NOT change or destabilise the existing live rehearsal capture, real-time analysis, or report flow.
- **FR-014**: Re-uploading a video for a session MUST replace that session's prior batch analysis results rather than accumulate duplicates.

### Constitution-Aligned Requirements *(mandatory)*

- **CAR-001**: Affects the core demo path by adding a new entry — **video upload + batch analysis** — that feeds the existing **session end → `/session/:id/report`** flow. The live rehearsal capture path is unaffected (FR-013).
- **CAR-002**: Changes the input contract by adding a video-upload interface and session processing-state reporting. The report payload, scoring, agent payloads (transcript/video/audio/slide/content), and DB row shapes are reused unchanged — the batch path produces the same rows the live path does.
- **CAR-003**: Video upload and processing-state reads MUST be scoped to the owning session and require the session `access_token`, exactly like the existing PPTX upload and session endpoints. Report sharing continues via `share_token`. No new cross-session access.
- **CAR-004**: Batch analysis runs off the live path with bounded, demo-safe behaviour: per-provider failure handling, partial-report degradation, explicit failure state, and `DEMO_MODE=replay` bypass. The live real-time fallbacks (`/health`, WS reconnect, audio-only, replay) remain intact.
- **CAR-005**: User-facing processing/ready/failure states and the report MUST not rely on color alone to convey meaning; states MUST be conveyed with text consistent with existing accessibility rules.

### Key Entities *(include if feature involves data)*

- **Uploaded Rehearsal Video**: The single video file a presenter submits for a session — its format, duration, and size are validated before analysis. Its embedded audio track is the speech source; its frames are the visual source. Not retained beyond what is needed to produce the report.
- **Session Processing State**: The lifecycle of an uploaded-video analysis for a session — accepted → processing → ready (or failed, with a reason) — used to gate report availability and inform the presenter.
- **Derived Analysis Rows** (reused, not new): the transcript entries, video observations, audio warnings, slide analyses, and content analysis that the batch path writes for the session — identical in shape to those the live path writes, so the report is assembled the same way.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A presenter can go from "session with analysed deck" to a viewable report by uploading a video, with no live rehearsal, in a single guided flow.
- **SC-002**: For an uploaded video, the report contains the same score categories (voice, body, slide, content) and the same insight structure as a live-session report — verifiable by comparing report shape, not values.
- **SC-003**: Every insight timestamp for an uploaded video falls within the video's duration and corresponds to the referenced moment in the recording.
- **SC-004**: A 15-minute video is accepted and fully processed to a ready report; videos beyond 15 minutes or unsupported formats are rejected within a few seconds of upload.
- **SC-005**: 100% of uploaded-video analyses end in a terminal state (ready or failed-with-reason) — none hang indefinitely — and a processing failure never affects the live path or other sessions.
- **SC-006**: With demo replay enabled, an uploaded video yields a complete report using fixtures and makes no live AI/STT calls.

## Assumptions

- A given session is analysed by exactly one path: either a live rehearsal or an uploaded video. Mixing both in one session is out of scope for this phase; if a video is uploaded, it is the analysis source for that session.
- The same analysis agents, scoring rubric, report structure, and database schema are reused; the batch path differs only in how frames and audio reach those agents (from a file and its media timeline rather than a live stream).
- Live in-progress feedback is intentionally excluded for uploaded videos in this phase and may be added later.
- The audio source for speech analysis is the video's embedded audio track; presenters do not upload audio separately.
- Maximum supported duration is 15 minutes for this phase; a file-size limit consistent with that duration applies (a concrete byte limit is set during planning).
- Supported formats are the common consumer outputs (typical YouTube downloads, QuickTime/screen-recorder exports); exotic or professional container/codec combinations are out of scope and rejected.
- Uploaded media is processed transiently to produce the report and is not offered as a long-term stored asset in this phase.

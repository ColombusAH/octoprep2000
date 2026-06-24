# Feature Specification: Report PDF Download

**Feature Branch**: `002-report-pdf-download`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "when user see the final report i want the user to be able to download the report to pdf"

## Overview

Presenters who finish a rehearsal and view their scored session report should be able to
download that report as a PDF file. The download gives them a portable, offline copy they
can save, print, or share outside the application — without needing to return to the live
report URL.

This feature extends the existing report screen (`/session/:id/report`) with a clear
download action. The PDF MUST reflect the same information the presenter sees in the
on-screen scorecard: overall score, mentor lock/unlock status, sub-category scores, and
strengths/improvements with their timestamp and slide references.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Download report as PDF after session (Priority: P1)

A presenter completes a rehearsal, waits for the report to finish processing, and lands
on the session report page. They tap or click a download control and receive a PDF file
containing their full scorecard.

**Why this priority**: This is the core user request. Without a working download action,
the feature delivers no value.

**Independent Test**: Open any completed session report, trigger download, and confirm a
valid PDF file is saved to the device with recognizable report content.

**Acceptance Scenarios**:

1. **Given** a completed report is visible on screen, **When** the presenter selects
   "Download PDF" (or equivalent), **Then** a PDF file is saved to their device.
2. **Given** a download is in progress, **When** the presenter waits, **Then** they see
   clear feedback that generation is underway and the control is not double-triggered.
3. **Given** a download completes successfully, **When** the presenter opens the file,
   **Then** the filename identifies the session (e.g. includes session identifier or
   report date).

---

### User Story 2 - PDF matches on-screen report content (Priority: P1)

A presenter downloads their report and compares it to what they saw in the browser. The
PDF contains the same substantive feedback — not a blank page, truncated summary, or
unrelated content.

**Why this priority**: A download that omits scores or feedback defeats the purpose of
exporting the report.

**Independent Test**: Download a PDF for a report with known scores and insights; verify
each visible on-screen section appears in the PDF with matching values and text.

**Acceptance Scenarios**:

1. **Given** a report showing an overall score and four sub-category panels, **When**
   the PDF is generated, **Then** the overall score and each scored sub-category score
   appear in the document.
2. **Given** a report with strengths and improvements (including timestamp and slide
   citations), **When** the PDF is generated, **Then** those insight messages and
   references are included.
3. **Given** a report where the mentor is locked or unlocked, **When** the PDF is
   generated, **Then** the mentor status and associated messaging are reflected
   (booking link MAY appear as plain text or URL rather than an interactive button).
4. **Given** a report where body language was not scored (camera unavailable), **When**
   the PDF is generated, **Then** the "not scored" state for that category is shown
   consistently with the on-screen report.
5. **Given** the on-screen disclaimer about AI training cutoff, **When** the PDF is
   generated, **Then** an equivalent disclaimer appears in the document.

---

### User Story 3 - Download works across common devices (Priority: P2)

A presenter on a laptop or mobile phone downloads their report without needing special
software beyond a standard browser.

**Why this priority**: Presenters may review reports on phones after a rehearsal; export
must not be desktop-only.

**Independent Test**: Trigger download from a mobile viewport and a desktop viewport;
confirm a PDF is received on both.

**Acceptance Scenarios**:

1. **Given** a presenter on a mobile browser, **When** they download the report, **Then**
   the file saves or opens via the device's normal download behavior.
2. **Given** a presenter on a desktop browser, **When** they download the report, **Then**
   the file appears in the browser's download location.

---

### Edge Cases

- What happens when PDF generation fails (browser limitation, memory, or timeout)?
  The user sees a clear error message and can retry; the on-screen report remains usable.
- What happens when the report has many insights (long content)?
  The PDF spans multiple pages with readable layout rather than clipping or overlapping text.
- What happens when the presenter views the report via a shared read-only link?
  Download is not offered on shared-link views in this release (report owner only).
- What happens if the user triggers download before the report has fully rendered?
  Download is only available once the complete report is displayed (same gate as the
  visible scorecard).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a visible download action on the completed session
  report page for the report owner (non-shared view).
- **FR-002**: The system MUST generate a PDF document containing the presenter's session
  report when the download action is selected.
- **FR-003**: The PDF MUST include the overall score, mentor lock/unlock status and
  messaging, all four sub-category sections, sub-category scores (or "not scored"
  state), strengths, improvements, timestamp references, slide references, and the AI
  content disclaimer shown on screen.
- **FR-004**: The downloaded file MUST use a human-readable filename that includes a
  session identifier and/or report date so users can distinguish exports.
- **FR-005**: The system MUST show in-progress feedback while the PDF is being prepared
  and prevent duplicate simultaneous downloads from the same action.
- **FR-006**: The system MUST display a user-friendly error message if PDF generation
  fails, without disrupting the on-screen report.
- **FR-007**: The download action MUST NOT be shown on shared read-only report views
  (`?share=` links) in this release.
- **FR-008**: The PDF layout MUST remain readable when printed (legible text size,
  sufficient contrast, no critical content cut off at page edges).

### Constitution-Aligned Requirements *(mandatory)*

- **CAR-001**: This feature affects the core demo path at `/session/:id/report` only.
  It extends the report delivery surface without changing upload, live capture, session
  end, or report generation logic. The end-to-end demo path (upload → rehearse → report)
  MUST remain intact.
- **CAR-002**: No change to API, WebSocket, agent payload, shared type, scoring, or
  database contracts is required. PDF export is a presentation-layer concern that reads
  the already-rendered report data.
- **CAR-003**: Download is available only on the private report view where the presenter
  holds a valid session `access_token`. Shared `share_token` read-only views MUST NOT
  expose download in this release.
- **CAR-004**: PDF generation is not on the live-session path. On failure, the system
  degrades gracefully: the on-screen report remains fully functional and the user may
  retry download. No external AI or STT providers are involved.
- **CAR-005**: The download control MUST have an accessible label (not icon-only without
  text alternative), MUST be keyboard-activatable, and MUST not rely on color alone to
  convey its purpose or state (loading, success, error).

### Key Entities

- **Session Report**: The scored feedback artifact for a rehearsal — overall score,
  sub-category scores, insights, mentor unlock state — already displayed on the report
  page.
- **PDF Export**: A downloadable file snapshot of the session report, generated on
  demand from the visible report content at the time of download.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Presenters can initiate and receive a PDF download within 10 seconds for a
  typical report (up to four sub-categories with up to 20 insight items total) on a
  standard broadband connection.
- **SC-002**: 100% of on-screen report sections (hero score, mentor status, four
  sub-category panels, disclaimer) appear in the downloaded PDF for reports that include
  those sections.
- **SC-003**: At least 90% of test users can locate and complete a download on first
  attempt without assistance (measured in manual QA across desktop and mobile).
- **SC-004**: Downloaded PDFs are legible when printed on A4 or US Letter paper without
  horizontal scrolling or unreadable text (verified in manual print preview).
- **SC-005**: PDF generation failures do not block or replace the on-screen report;
  users can continue reading the report and retry download.

## Assumptions

- PDF export is generated from the report data already loaded on the report page; no
  new server-side report endpoint is required for the initial release.
- Only the report owner (authenticated via session `access_token`) needs download in
  v1; shared-link viewers are out of scope.
- The PDF is a static snapshot at download time; it does not update if the report data
  changes later.
- Standard modern browsers (Chrome, Safari, Firefox, Edge — current and previous major
  version) are the target; legacy browser support is not required.
- Multi-page PDFs are acceptable for long reports; single-page compression is not a
  requirement.
- Interactive elements (celebration animation, booking button) MAY be represented as
  static text or URLs in the PDF rather than interactive controls.

## Dependencies

- Completed session report UI and data at `/session/:id/report` (existing `ScoreCard`
  and report API).
- PRD FR-009 stretch item: "Export as PDF" — this feature formalizes that stretch goal.

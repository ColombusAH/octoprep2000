# Phase 0 Research: Report PDF Download

**Feature**: 002-report-pdf-download
**Date**: 2026-06-24

## Context recap (from current code)

- Report page: `packages/web-dashboard/app/routes/session.$id_.report.tsx`
- Renders `ScoreCard` after `revealReport` gate with `ReportData` from `getReport(id, share)`
  and `PublicConfig` from `getPublicConfig()`.
- `ReportData` shape (`ScoreCard.tsx`): `overall_score`, `voice_score`, `body_score`,
  `slide_score`, `content_score`, `insights[]`, `mentor_unlocked`.
- Header already has **Copy share link** button when `!share` (owner view).
- No PDF-related dependencies in `package.json` today.
- PRD FR-009 stretch: "Export as PDF" — this feature implements it.

**Conclusion**: All data needed for PDF export is already in client state. The work is
presentation-layer: generate a print-friendly document and trigger a browser download.

---

## Decision 1 — PDF generation library: `@react-pdf/renderer`

**Decision**: Use `@react-pdf/renderer` to build a dedicated `ReportPdfDocument` React
component that renders from `ReportData` + `mentorBookingUrl`, then call `pdf().toBlob()`
to produce the downloadable file.

**Rationale**:
- Spec assumes client-side export from loaded report data (Assumptions section).
- Constitution Principle V prefers minimal abstractions; one focused library beats a
  server-side PDF service or a two-library canvas stack.
- The web scorecard uses a dark theme (`text-pearl`, teal accents). DOM-screenshot
  approaches produce low-contrast print output; a dedicated PDF layout uses a light
  background and readable typography (FR-008, SC-004).
- `@react-pdf/renderer` handles multi-page documents natively (edge case: many insights).
- Filename control (`octoprep-report-{id}-{date}.pdf`) is straightforward via blob download.

**Alternatives considered**:
- **`window.print()` + `@media print` CSS** — rejected: opens the system print dialog, not
  a direct file download (FR-002, user expectation).
- **`html2canvas` + `jspdf`** — rejected: WYSIWYG from dark UI prints poorly; canvas
  rendering is flaky on mobile Safari; two dependencies with larger bundle.
- **Server-side PDF (WeasyPrint, Puppeteer, ReportLab)** — rejected: new backend endpoint,
  latency, deployment complexity; violates CAR-002 "presentation-layer only" assumption.
- **`pdfmake` (JSON → PDF)** — viable but less ergonomic with existing React component
  mental model; `@react-pdf/renderer` maps cleanly to the panel structure in `ScoreCard`.

---

## Decision 2 — Layout strategy: parallel PDF component, not DOM clone

**Decision**: Create `ReportPdfDocument.tsx` that mirrors `ScoreCard` section structure
(hero score, mentor status, four category panels, disclaimer) but with print-optimized
styling. Extract shared pure helpers (`formatTs`, category titles) into
`reportFormatting.ts` used by both `ScoreCard` and the PDF document.

**Rationale**:
- Guarantees content parity (FR-003, SC-002) via the same `ReportData` input.
- Avoids coupling PDF quality to web CSS (dark theme, animations, `CornerBrackets`).
- Mentor booking CTA becomes plain text + URL string in PDF (per spec assumption).

**Alternatives considered**:
- **Screenshot the mounted `ScoreCard` DOM** — rejected: see Decision 1 rationale.
- **Single shared React component for web + PDF** — rejected: `@react-pdf/renderer` uses
  its own primitives (`Document`, `Page`, `Text`); forcing one component tree serves
  neither surface well.

---

## Decision 3 — Download UX: blob anchor + guarded state machine

**Decision**: Export helper `exportReportPdf({ sessionId, report, mentorBookingUrl })`:
1. Set status → `generating`
2. `const blob = await pdf(<ReportPdfDocument ... />).toBlob()`
3. Create temporary `<a download>` with filename
   `octoprep-report-{sessionId.slice(0,8)}-{YYYY-MM-DD}.pdf`
4. Revoke object URL after click
5. Set status → `idle` (or `error` on catch)

Button disabled while `generating`; `aria-busy="true"` during generation.

**Rationale**: Matches FR-005 (in-progress feedback, no double-trigger) and FR-006
(graceful error). Standard browser download pattern works on desktop and mobile.

**Alternatives considered**:
- **`pdf().toBuffer()` server-side** — N/A (no server).
- **Open PDF in new tab instead of download** — rejected: spec says "saved to device"
  (US1 acceptance scenario).

---

## Decision 4 — Visibility gate: owner view only

**Decision**: Render the download button only when `!share` (same condition as the share
button). Shared read-only views never show download.

**Rationale**: Matches FR-007, CAR-003, and Mission Brief scope. Share viewers already
lack `access_token`; export is a presenter-only affordance.

---

## Decision 5 — No backend or shared-types changes

**Decision**: Zero changes to `packages/backend`, `packages/shared-types`, or database.

**Rationale**: CAR-002. PDF is a client-side snapshot of data already returned by
`GET /sessions/:id/report`. Re-fetching before export is optional (data is in React state).

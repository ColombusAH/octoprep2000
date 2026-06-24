# Phase 1 Data Model: Report PDF Download

**Feature**: 002-report-pdf-download
**Date**: 2026-06-24

> No database schema changes. This document maps existing in-memory types to the PDF
> export surface and defines client-side export state.

## Source entities (unchanged — from API)

### ReportData

Already defined in `packages/web-dashboard/app/components/ScoreCard.tsx` and returned by
`GET /sessions/:id/report`.

| Field | Type | PDF section |
|---|---|---|
| `overall_score` | number | Hero header — large score display |
| `voice_score` | number | Voice & Delivery panel |
| `body_score` | number \| null | Body Language panel (`null` → "Not scored") |
| `slide_score` | number | Slide Quality panel |
| `content_score` | number | Technical Content panel |
| `mentor_unlocked` | boolean | Mentor locked/unlocked messaging |
| `insights` | `Insight[]` | Strengths / Improvements per category |

### Insight

| Field | Type | PDF rendering |
|---|---|---|
| `category` | `"voice" \| "body" \| "slide" \| "content"` | Routes to correct panel |
| `type` | `"STRENGTH" \| "IMPROVEMENT"` | Section within panel |
| `message` | string | Body text |
| `timestamps` | `number[]` (optional) | Formatted as `M:SS` list |
| `slides` | `number[]` (optional) | `slides 1, 3, 5` suffix |

### PublicConfig (export input)

| Field | Type | PDF use |
|---|---|---|
| `mentor_booking_url` | string | Plain URL when `mentor_unlocked === true` |

## New client-side types

### PdfExportInput

Arguments passed to the export helper.

| Field | Type | Validation |
|---|---|---|
| `sessionId` | string | Non-empty; used in filename |
| `report` | `ReportData` | Must match loaded scorecard |
| `mentorBookingUrl` | string | From `PublicConfig` |

### PdfExportStatus

UI state for the download control.

| Value | Meaning | UI behavior |
|---|---|---|
| `idle` | Ready | Button enabled, label "Download PDF" |
| `generating` | PDF in flight | Button disabled, `aria-busy`, label "Generating…" |
| `error` | Last attempt failed | Button enabled, inline error message, retry allowed |

**State transitions**:

```
idle ──click──▶ generating ──success──▶ idle
                    │
                    └──failure──▶ error ──click──▶ generating
```

### PdfFilename

Computed at export time (not persisted):

```
octoprep-report-{sessionIdPrefix}-{YYYY-MM-DD}.pdf
```

- `sessionIdPrefix` = first 8 characters of `sessionId`
- Date = local date at generation time

## Content parity checklist (PDF ↔ ScoreCard)

| ScoreCard section | PDF must include |
|---|---|
| `ScoreRing` + overall score | Numeric overall score |
| Mentor lock/unlock card | Status text + delta or booking URL |
| Voice panel | Score bar equivalent + strengths/improvements |
| Body panel | Score or "Not scored — camera unavailable" |
| Slide panel | Score + insights |
| Content panel | Score + insights |
| Footer disclaimer | Same AI cutoff disclaimer text |

## Validation rules

- Export MUST NOT start unless `report` and `mentorBookingUrl` are both defined (same
  gate as `revealReport`).
- Export MUST NOT be offered when `share` search param is present.
- `generating` state MUST block concurrent export attempts (FR-005).
- On `body_score === null` with no body insights, PDF shows the not-scored message (FR-003
  scenario 4).

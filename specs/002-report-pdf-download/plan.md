# Implementation Plan: Report PDF Download

**Branch**: `exports` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/002-report-pdf-download/spec.md`

## Summary

Add a **Download PDF** action to the completed session report page (`/session/:id/report`).
When the presenter clicks it, the browser generates and saves a PDF snapshot of their
scorecard using the `ReportData` already loaded for `ScoreCard`. Implementation is
**frontend-only**: a dedicated print-friendly PDF document component built with
`@react-pdf/renderer`, a small export helper, and a download button in the report header
(next to the existing share control). No backend, database, or API contract changes.

## Technical Context

**Language/Version**: TypeScript / React 18 (TanStack Start frontend); backend untouched
**Primary Dependencies**: `@react-pdf/renderer` (new); existing `ReportData` type from
`ScoreCard`, `lucide-react`, shadcn `Button`
**Storage**: N/A — PDF generated in-browser from in-memory report state; no persistence
**Testing**: `pnpm --filter @octoprep/web-dashboard lint` (tsc); manual QA per quickstart.md
**Target Platform**: Modern desktop + mobile browsers (Chrome, Safari, Firefox, Edge)
**Project Type**: Monorepo web app; change is frontend-only in `packages/web-dashboard`
**Performance Goals**: PDF ready within 10 seconds for a typical report (SC-001)
**Constraints**: Report owner view only (`!share`); graceful error on generation failure;
print-legible layout (light background, ≥11pt body text); one new dependency justified
**Scale/Scope**: ~4 new/edited frontend files; no backend or shared-types changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Demo-First Vertical Slices | PASS | Extends report delivery only. Upload → rehearse → end → report path unchanged. Independently demonstrable slice. |
| II. Contracted Agent Boundaries | PASS | No agent, WebSocket, or Orchestrator changes. PDF reads existing `ReportData` from `GET /sessions/:id/report`. |
| III. Session Isolation & Explicit Sharing | PASS | Download shown only when `share` query param absent (private owner view). Shared `?share=` views hide download (FR-007). |
| IV. Resilience Before Polish | PASS | Not on live-session path. PDF failure shows error + retry; on-screen report unaffected (FR-006, CAR-004). |
| V. Native Stack, Minimal Abstractions | PASS (with justification) | One new dep (`@react-pdf/renderer`) vs server-side PDF or html2canvas stack. See research Decision 1 + Complexity Tracking. |

**Gate result**: All gates pass. Proceed to implementation after `/spec-tasks`.

### Post-design re-check (Phase 1)

| Check | Status |
|---|---|
| Demo path preserved | PASS — button added after `revealReport` gate only |
| No API/DB contract changes | PASS — `contracts/pdf-export-contract.md` is UI-only |
| Session isolation | PASS — `share` param gates download visibility |
| Resilience | PASS — `PdfExportStatus` error state + retry |
| Stack simplicity | PASS — single focused dependency, no new service |
| Validation | PASS — quickstart.md covers desktop/mobile + mock fixtures |

## Project Structure

### Documentation (this feature)

```text
specs/002-report-pdf-download/
├── plan.md              # This file
├── spec.md              # Feature spec
├── research.md          # Phase 0 — PDF library + layout decisions
├── data-model.md        # Phase 1 — ReportData mapping + export state
├── quickstart.md        # Phase 1 — validation scenarios
├── contracts/
│   └── pdf-export-contract.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
packages/web-dashboard/
├── package.json                          # +@react-pdf/renderer
├── app/
│   ├── routes/
│   │   └── session.$id_.report.tsx       # Download button + export handler
│   ├── components/
│   │   ├── ScoreCard.tsx                 # (optional) extract shared format helpers
│   │   └── ReportPdfDocument.tsx         # NEW — print-friendly PDF layout
│   └── lib/
│       ├── exportReportPdf.ts            # NEW — generate blob + trigger download
│       └── reportFormatting.ts           # NEW — shared formatTs, category labels
```

**Structure Decision**: Frontend-only change in `packages/web-dashboard`. PDF layout is a
separate component (not a DOM screenshot) so print output is legible regardless of the
dark-themed web UI. Shared formatting helpers avoid drift between `ScoreCard` and PDF.

## Triage Framework: [SYNC] vs [ASYNC] Classification

**Execution Strategy**: Mostly agent-delegated; human review for PDF visual QA on desktop
and mobile.

### Preliminary Task Classification

| Task Category | Estimated [SYNC] Tasks | Estimated [ASYNC] Tasks | Rationale |
|---------------|----------------------|----------------------|-----------|
| Business Logic | 0 | 1 | Export helper + filename logic is straightforward. |
| Data Operations | 0 | 0 | No DB changes. |
| UI Components | 1 | 2 | PDF layout + button wiring; human reviews print output. |
| Integrations | 0 | 0 | No external APIs. |
| Infrastructure | 0 | 1 | Add `@react-pdf/renderer` dependency. |

### Triage Audit Trail

| Task | Classification | Primary Criteria | Risk Level | Rationale |
|------|----------------|------------------|------------|-----------|
| Add `@react-pdf/renderer` | ASYNC | Dependency install | Low | Standard npm add. |
| `ReportPdfDocument.tsx` | SYNC | Visual/UX correctness | Med | Print layout must match spec content checklist. |
| `exportReportPdf.ts` | ASYNC | Mechanical helper | Low | Blob + anchor download pattern. |
| Report page button | ASYNC | UI wiring | Low | Mirrors share button pattern. |
| Manual QA (desktop + mobile) | SYNC | Constitution validation gate | Med | Required per CAR-005 + SC-003/SC-004. |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New dependency `@react-pdf/renderer` | Structured, multi-page, print-legible PDF from `ReportData` without a backend endpoint | `window.print()` + CSS — opens print dialog, not a file download (FR-002). `html2canvas` + `jspdf` — poor fidelity on dark-themed UI, heavier combo, layout bugs on mobile. Server-side PDF — new endpoint + infra, violates CAR-002 assumption. |

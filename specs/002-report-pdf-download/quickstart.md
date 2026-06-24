# Quickstart / Validation: Report PDF Download

**Feature**: 002-report-pdf-download

Run guide proving PDF export end-to-end. Implementation details live in `tasks.md` (after
`/spec-tasks`); this file is the validation harness.

## Prerequisites

- `make install` done.
- Backend + frontend running, **or** dev mock mode (no backend required for UI-only checks).
- Feature implemented per `plan.md` and `contracts/pdf-export-contract.md`.

## Setup

```bash
make dev
# or frontend-only with mocks:
cd packages/web-dashboard && pnpm dev
```

## Scenario 1 — Download from completed report (US1, SC-001)

1. Open a completed session report at `/session/{id}/report` (owner view, no `?share=`).
2. Click **Download PDF**.
3. **Expected**:
   - Button shows "Generating…" and is disabled during export.
   - A `.pdf` file downloads within 10 seconds.
   - Filename matches `octoprep-report-{idPrefix}-{date}.pdf`.

## Scenario 2 — PDF content parity (US2, SC-002)

Use dev mock fixtures for deterministic content:

```
http://localhost:3000/session/dev-mock/report?mock=unlocked
http://localhost:3000/session/dev-mock/report?mock=locked
http://localhost:3000/session/dev-mock/report?mock=no-camera
```

For each mock, download PDF and verify:

| Section | Present |
|---|---|
| Overall score | ✓ matches on-screen value |
| Mentor status | ✓ locked delta or unlocked + URL |
| Voice panel + score | ✓ |
| Body panel | ✓ score or "not scored" for `no-camera` |
| Slide panel + score | ✓ |
| Content panel + score | ✓ |
| Strengths / improvements | ✓ messages + timestamp/slide refs |
| AI disclaimer | ✓ |

## Scenario 3 — Shared view hides download (FR-007, CAR-003)

1. Open `/session/{id}/report?share={token}`.
2. **Expected**: No Download PDF button. Share link button also hidden (existing behavior).

## Scenario 4 — Mobile download (US3)

1. Open report in Chrome DevTools device mode (e.g. iPhone 14) or a real phone.
2. Download PDF.
3. **Expected**: File saves or opens via native mobile download behavior.

## Scenario 5 — Error recovery (FR-006, SC-005)

1. (Dev) Temporarily throw inside `exportReportPdf` or block `@react-pdf/renderer` import.
2. Click Download PDF.
3. **Expected**:
   - Error message visible (`role="alert"`).
   - Scorecard still fully visible and scrollable.
   - Retry succeeds after fixing the error.

## Scenario 6 — Print legibility (SC-004)

1. Download PDF from `?mock=locked`.
2. Open in Preview/Acrobat → Print Preview (A4 or Letter).
3. **Expected**: No horizontal scroll; body text readable; no clipped panel headers.

## Scenario 7 — Core demo path regression (CAR-001)

1. Run full demo path: upload PPTX → rehearse → end session → view report.
2. **Expected**: Report loads as before; PDF download is additive only.

## Lint

```bash
pnpm --filter @octoprep/web-dashboard lint
```

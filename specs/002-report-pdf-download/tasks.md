# Tasks: Report PDF Download

**Input**: Design documents from `/specs/002-report-pdf-download/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Manual QA per quickstart.md; `pnpm --filter @octoprep/web-dashboard lint`

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add dependency and shared formatting helpers

- [X] T001 Add `@react-pdf/renderer` dependency in `packages/web-dashboard/package.json`
- [X] T002 [P] Create shared formatting helpers in `packages/web-dashboard/app/lib/reportFormatting.ts`
- [X] T003 [P] Refactor `ScoreCard.tsx` to use `reportFormatting.ts` helpers

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core export infrastructure before user story wiring

- [X] T004 Create PDF document component in `packages/web-dashboard/app/components/ReportPdfDocument.tsx`
- [X] T005 Create export helper in `packages/web-dashboard/app/lib/exportReportPdf.tsx`

**Checkpoint**: PDF generation works standalone from mock `ReportData`

---

## Phase 3: User Story 1 - Download report as PDF after session (Priority: P1) 🎯 MVP

**Goal**: Presenter clicks Download PDF and receives a valid file with recognizable content

**Independent Test**: Open completed report, trigger download, confirm `.pdf` saved with correct filename

### Implementation for User Story 1

- [X] T006 [US1] Add download button, `PdfExportStatus` state, and handler in `packages/web-dashboard/app/routes/session.$id_.report.tsx`
- [X] T007 [US1] Wire `exportReportPdf` call with generating/idle state and duplicate-click guard in `packages/web-dashboard/app/routes/session.$id_.report.tsx`

**Checkpoint**: Download works end-to-end on owner view

---

## Phase 4: User Story 2 - PDF matches on-screen report content (Priority: P1)

**Goal**: PDF contains all scorecard sections with matching values and text

**Independent Test**: Download from `?mock=locked`, `?mock=unlocked`, `?mock=no-camera`; verify all sections

### Implementation for User Story 2

- [X] T008 [US2] Implement full content parity in `packages/web-dashboard/app/components/ReportPdfDocument.tsx` (hero, mentor, four panels, disclaimer)
- [X] T009 [US2] Handle `body_score === null` not-scored state in `packages/web-dashboard/app/components/ReportPdfDocument.tsx`

**Checkpoint**: PDF content matches ScoreCard for all mock fixtures

---

## Phase 5: User Story 3 - Download works across common devices (Priority: P2)

**Goal**: Blob anchor download pattern works on desktop and mobile browsers

**Independent Test**: Trigger download in desktop and mobile viewport; file saves via native behavior

### Implementation for User Story 3

- [X] T010 [US3] Ensure blob download + object URL cleanup in `packages/web-dashboard/app/lib/exportReportPdf.tsx` uses standard anchor pattern

**Checkpoint**: Mobile and desktop download behavior verified per quickstart Scenario 4

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, visibility gates, validation

- [X] T011 Hide download on shared `?share=` views in `packages/web-dashboard/app/routes/session.$id_.report.tsx`
- [X] T012 Add error display with `role="alert"` and retry on failure in `packages/web-dashboard/app/routes/session.$id_.report.tsx`
- [X] T013 Run `pnpm --filter @octoprep/web-dashboard lint` and fix any type errors

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on T001–T003
- **User Stories (Phase 3–5)**: Depend on Phase 2
- **Polish (Phase 6)**: Depends on all user stories

### User Story Dependencies

- **US1**: Core download flow — MVP
- **US2**: Content in ReportPdfDocument — can overlap with US1 wiring
- **US3**: Export helper pattern — largely in T005/T010

### Parallel Opportunities

- T002 and T003 can run in parallel after T001
- T004 and T005 can run in parallel after Phase 1

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1 + Phase 2
2. Complete Phase 3 (T006–T007)
3. Validate download on owner view

### Incremental Delivery

1. Add US2 content parity (T008–T009)
2. Add US3 mobile pattern (T010)
3. Polish error handling and lint (T011–T013)

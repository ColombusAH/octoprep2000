# Contract: Report PDF Export (UI)

**Feature**: 002-report-pdf-download

Client-side contract between the report page, export helper, and PDF document component.
No HTTP or WebSocket changes.

## Entry point

**Route**: `/session/:id/report` (owner view, no `?share=` param)

**Trigger**: User activates the download control in the report header.

## Inputs

```typescript
type PdfExportInput = {
  sessionId: string;
  report: ReportData;       // from GET /sessions/:id/report
  mentorBookingUrl: string; // from GET /config
};
```

`ReportData` is the existing type exported from `~/components/ScoreCard`.

## Export function

**Module**: `~/lib/exportReportPdf.ts`

```typescript
export async function exportReportPdf(input: PdfExportInput): Promise<void>;
```

**Behavior**:
1. Build `<ReportPdfDocument report={...} mentorBookingUrl={...} sessionId={...} />`.
2. Call `@react-pdf/renderer` `pdf(...).toBlob()`.
3. Trigger browser download with filename
   `octoprep-report-{sessionId.slice(0,8)}-{YYYY-MM-DD}.pdf`.
4. Throw on failure (caller sets `PdfExportStatus` → `error`).

## PDF document component

**Module**: `~/components/ReportPdfDocument.tsx`

```typescript
export function ReportPdfDocument(props: {
  sessionId: string;
  report: ReportData;
  mentorBookingUrl: string;
}): React.ReactElement; // @react-pdf Document tree
```

**Required sections** (order):
1. Title: "OctoPrep2000 — Session Report"
2. Session ID (truncated) + generation date
3. Overall score (numeric, prominent)
4. Mentor status block (locked with delta, or unlocked with URL)
5. Four category panels (voice, body, slide, content)
6. AI content disclaimer (matches ScoreCard footer)

**Styling constraints**:
- Light background (`#ffffff`), dark text (`#111111`)
- Body text ≥ 11pt; headings ≥ 14pt
- Page breaks allowed between panels

## Download control (report page)

**Location**: Report header, adjacent to "Copy share link"

| Prop / condition | Value |
|---|---|
| Visible when | `revealReport && report && config && !share` |
| Label (idle) | `Download PDF` |
| Label (generating) | `Generating…` |
| Disabled when | `pdfStatus === "generating"` |
| `aria-busy` | `true` when generating |
| Error display | Inline `role="alert"` below header buttons on failure |

## Visibility matrix

| View | Share param | Download shown |
|---|---|---|
| Owner (has `access_token`) | absent | Yes |
| Shared read-only | `?share=...` | No |

## Non-goals (this release)

- No `GET /sessions/:id/report.pdf` endpoint
- No PDF export on shared links
- No email/send integration
- No server-side PDF storage

## Error contract

On export failure, the page:
- MUST keep `ScoreCard` rendered and interactive
- MUST show a user-facing message (e.g. "Could not generate PDF — try again")
- MUST allow retry without page reload

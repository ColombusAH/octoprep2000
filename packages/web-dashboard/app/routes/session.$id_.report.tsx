import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { createShareLink, getPublicConfig, getReport, type PublicConfig } from "~/lib/api";
import { ScoreCard, type ReportData } from "~/components/ScoreCard";
import { Button } from "~/components/ui/button";
import { MOCK_REPORTS, MOCK_CONFIG } from "~/lib/mockReportData";

export const Route = createFileRoute("/session/$id_/report")({
  component: ReportPage,
  validateSearch: (search): { share?: string; mock?: string } => ({
    share: typeof search.share === "string" ? search.share : undefined,
    mock: typeof search.mock === "string" ? search.mock : undefined,
  }),
});

function ReportPage() {
  const { id } = Route.useParams();
  const { share, mock } = Route.useSearch();
  // Dev-only: ?mock=unlocked|locked|no-camera renders a fixture instead of calling the
  // backend, so the report screen's visual states can be iterated on without a live
  // rehearsal. Gated by DEV so it never ships in a production build.
  const mockReport = import.meta.env.DEV && mock ? MOCK_REPORTS[mock] : undefined;
  const [report, setReport] = useState<ReportData | null>(mockReport ?? null);
  const [config, setConfig] = useState<PublicConfig | null>(mockReport ? MOCK_CONFIG : null);
  const [error, setError] = useState<string | null>(
    mockReport === undefined && mock ? `Unknown mock key "${mock}"` : null,
  );
  const [shareUrl, setShareUrl] = useState<string | null>(null);

  useEffect(() => {
    if (mockReport) return;
    let stop = false;
    Promise.all([getReport(id, share), getPublicConfig()])
      .then(([r, c]) => {
        if (stop) return;
        setReport(r);
        setConfig(c);
      })
      .catch((err) => {
        if (!stop) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      stop = true;
    };
  }, [id, share, mockReport]);

  const handleShare = async () => {
    try {
      const { share_url } = await createShareLink(id);
      setShareUrl(share_url);
      navigator.clipboard?.writeText(window.location.origin + share_url).catch(() => undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  if (error) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Report</h1>
        <p className="mt-3 text-sm text-destructive" role="alert">
          {error}
        </p>
      </main>
    );
  }

  if (!report || !config) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-10">
        <p className="text-sm text-muted-foreground">Generating report…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Session Report</h1>
        {!share && (
          <Button variant="outline" onClick={handleShare}>
            {shareUrl ? "Link copied ✓" : "Copy share link"}
          </Button>
        )}
      </header>
      <ScoreCard report={report} mentorBookingUrl={config.mentor_booking_url} />
    </main>
  );
}

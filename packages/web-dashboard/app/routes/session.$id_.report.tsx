import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ApiError, createShareLink, getPublicConfig, getReport, type PublicConfig } from "~/lib/api";
import { ScoreCard, type ReportData } from "~/components/ScoreCard";
import { ProcessingScreen } from "~/components/ProcessingScreen";
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
  // Hold the report-ready transition for one "complete" beat on ProcessingScreen
  // before swapping to ScoreCard, so the wait pays off instead of cutting away.
  const [revealReport, setRevealReport] = useState(false);

  useEffect(() => {
    if (!report || !config) return;
    const t = setTimeout(() => setRevealReport(true), 700);
    return () => clearTimeout(t);
  }, [report, config]);

  useEffect(() => {
    if (mockReport) return;
    let stop = false;

    const deadline = Date.now() + 60_000;
    const load = async () => {
      try {
        const [r, c] = await Promise.all([getReport(id, share), getPublicConfig()]);
        if (stop) return;
        setReport(r);
        setConfig(c);
      } catch (err) {
        if (stop) return;
        if (err instanceof ApiError && err.status === 404 && Date.now() < deadline) {
          window.setTimeout(load, 1_000);
          return;
        }
        setError(err instanceof Error ? err.message : String(err));
      }
    };

    load();
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
      <main className="mx-auto max-w-3xl px-8 py-10">
        <h1 className="font-display text-2xl font-bold tracking-tight text-pearl">Report</h1>
        <div className="mt-4 flex items-center gap-2.5 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 font-mono text-sm text-destructive" role="alert">
          <span className="rec-dot size-2 shrink-0 rounded-full bg-destructive motion-reduce:opacity-100" aria-hidden="true" />
          SIGNAL LOST — {error}
        </div>
      </main>
    );
  }

  if (!revealReport || !report || !config) {
    return (
      <main className="mx-auto max-w-3xl px-8 py-10">
        <h1 className="mb-6 font-display text-2xl font-bold tracking-tight text-pearl">
          Session Report
        </h1>
        <ProcessingScreen complete={!!(report && config)} />
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-5xl px-8 py-10">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold tracking-tight text-pearl">
          Session Report
        </h1>
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

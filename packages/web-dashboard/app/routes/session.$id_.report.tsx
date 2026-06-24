import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { ApiError, createShareLink, getPublicConfig, getReport, type Language, type PublicConfig } from "~/lib/api";
import { ScoreCard, type ReportData } from "~/components/ScoreCard";
import { ProcessingScreen } from "~/components/ProcessingScreen";
import { Button } from "~/components/ui/button";
import { MOCK_REPORTS, MOCK_CONFIG } from "~/lib/mockReportData";

type PdfExportStatus = "idle" | "generating" | "error";

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
  const [lang, setLang] = useState<Language | null>(mockReport ? "en" : null);
  // Hold the report-ready transition for one "complete" beat on ProcessingScreen
  // before swapping to ScoreCard, so the wait pays off instead of cutting away.
  const [revealReport, setRevealReport] = useState(false);
  const [pdfStatus, setPdfStatus] = useState<PdfExportStatus>("idle");
  const [pdfError, setPdfError] = useState<string | null>(null);

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
        setLang(r.language ?? "en");
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

  const handleToggleLang = async (next: Language) => {
    if (next === lang || mockReport) {
      setLang(next);
      return;
    }
    try {
      const r = await getReport(id, share, next);
      setReport(r);
      setLang(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleShare = async () => {
    try {
      const { share_url } = await createShareLink(id);
      setShareUrl(share_url);
      navigator.clipboard?.writeText(window.location.origin + share_url).catch(() => undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleDownloadPdf = async () => {
    if (!report || !config || pdfStatus === "generating") return;
    setPdfStatus("generating");
    setPdfError(null);
    try {
      const { exportReportPdf } = await import("../lib/exportReportPdf");
      await exportReportPdf({
        sessionId: id,
        report,
        mentorBookingUrl: config.mentor_booking_url,
      });
      setPdfStatus("idle");
    } catch (err) {
      setPdfStatus("error");
      setPdfError(err instanceof Error ? err.message : "Could not generate PDF — try again");
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
    <main className="mx-auto max-w-5xl px-8 py-10" dir={lang === "he" ? "rtl" : "ltr"}>
      <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-pearl">
            Session Report
          </h1>
          {report.topic && (
            <p className="mt-1 font-mono text-xs tracking-[0.08em] text-teal">{report.topic}</p>
          )}
        </div>
        <div className="flex flex-col items-stretch gap-2 sm:items-end">
          <div className="flex flex-wrap items-center gap-2.5">
          <div role="group" aria-label="Report language" className="inline-flex gap-1.5">
            <Button
              type="button"
              size="sm"
              variant={lang === "en" ? "default" : "outline"}
              aria-pressed={lang === "en"}
              onClick={() => handleToggleLang("en")}
            >
              EN
            </Button>
            <Button
              type="button"
              size="sm"
              variant={lang === "he" ? "default" : "outline"}
              aria-pressed={lang === "he"}
              onClick={() => handleToggleLang("he")}
            >
              עברית
            </Button>
          </div>
          {!share && (
            <>
              <Button
                variant="outline"
                onClick={handleDownloadPdf}
                disabled={pdfStatus === "generating"}
                aria-busy={pdfStatus === "generating"}
              >
                <Download className="size-4" aria-hidden="true" />
                {pdfStatus === "generating" ? "Generating…" : "Download PDF"}
              </Button>
              <Button variant="outline" onClick={handleShare}>
                {shareUrl ? "Link copied ✓" : "Copy share link"}
              </Button>
            </>
          )}
          </div>
          {pdfError && (
            <p className="text-sm text-destructive" role="alert">
              {pdfError}
            </p>
          )}
        </div>
      </header>
      <ScoreCard report={report} mentorBookingUrl={config.mentor_booking_url} />
    </main>
  );
}

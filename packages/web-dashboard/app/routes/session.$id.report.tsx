import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { createShareLink, getPublicConfig, getReport, type PublicConfig } from "~/lib/api";
import { ScoreCard, type ReportData } from "~/components/ScoreCard";

export const Route = createFileRoute("/session/$id/report")({
  component: ReportPage,
  validateSearch: (search): { share?: string } => ({
    share: typeof search.share === "string" ? search.share : undefined,
  }),
});

function ReportPage() {
  const { id } = Route.useParams();
  const { share } = Route.useSearch();
  const [report, setReport] = useState<ReportData | null>(null);
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);

  useEffect(() => {
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
  }, [id, share]);

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
      <main className="container">
        <h1>Report</h1>
        <p style={{ color: "var(--red)" }}>{error}</p>
      </main>
    );
  }

  if (!report || !config) {
    return (
      <main className="container">
        <p style={{ color: "var(--muted)" }}>Generating report…</p>
      </main>
    );
  }

  return (
    <main className="container">
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1>Session Report</h1>
        {!share && (
          <button onClick={handleShare} style={{ padding: "8px 14px", borderRadius: 8 }}>
            {shareUrl ? "Link copied ✓" : "Copy share link"}
          </button>
        )}
      </header>
      <ScoreCard report={report} mentorBookingUrl={config.mentor_booking_url} />
    </main>
  );
}
